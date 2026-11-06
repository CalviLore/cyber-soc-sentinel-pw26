"""Trascrizione di una sessione: domanda, passaggi dell'agente, risposta.

Dal log JSONL di un run costruisce righe nello stile di un terminale:

    mistral-large-4> Controlla l'IP 1.2.3.4: ...
    ● readLogs(ip="1.2.3.4", statusCode=401, limit=25)
      ⎿ riuscito: {"total": 50, "returned": 25, ...}
    ● isolateIp(ip="1.2.3.4", reason="brute force")
      [CONFERMA] Isolare l'IP 1.2.3.4? [Y/N] N (automatico)
      ⎿ riuscito: {"cancelled": true, ...}
    ● Ho proposto di isolare l'IP ma l'operatore ha rifiutato...
    arresto: risposta finale | giri: 3 | token: 4300 | tool: 2 riusciti, ...

Nulla e' inventato: ogni riga viene da un evento del log o dal risultato del
run. La usano la chat (per mostrare i passaggi) e il runner (per output.txt e
screenshot.png).
"""
import json
import re

from agent import formatSummary

LIMITE_VALORE = 60
LIMITE_RISULTATO = 170


def _valore(valore, limite=LIMITE_VALORE):
    testo = json.dumps(valore, ensure_ascii=False)  # le stringhe escono tra virgolette
    return testo if len(testo) <= limite else testo[: limite - 1] + "…"


def formattaChiamata(tool, argomenti):
    """readLogs(ip="1.2.3.4", limit=25): i valori lunghi vengono accorciati."""
    parti = ", ".join(f"{k}={_valore(v)}" for k, v in (argomenti or {}).items())
    return f"{tool}({parti})"


def _inUnaRiga(testo, limite=LIMITE_RISULTATO):
    piatto = " ".join(str(testo).split())
    return piatto if len(piatto) <= limite else piatto[: limite - 1] + "…"


# Alcuni modelli (Gemma) scrivono il ragionamento nel testo, tra tag come <thought>.
_PENSIERO = re.compile(r"<(thought|think|thinking)>(.*?)(?:</\1>|$)", re.DOTALL)


def separaPensiero(testo):
    """Divide il testo del modello in (pensiero, risposta).

    Il pensiero e' quello tra <thought>...</thought> (o <think>, <thinking>);
    la risposta e' il resto. Se non ci sono tag il pensiero e' vuoto.
    """
    if not testo:
        return "", ""
    pensieri = [m.group(2).strip() for m in _PENSIERO.finditer(testo)]
    risposta = _PENSIERO.sub("", testo).strip()
    return "\n\n".join(p for p in pensieri if p), risposta


def righeSessione(richiesta, eventi, result, *, modello=None, automatico=True,
                  mostraRichiesta=True, mostraConferme=True, mostraTool=True):
    """Lista di (stile, testo). Stili: prompt, tool, conferma, risultato,
    errore, ragiona, pensiero, risposta, riepilogo.

    automatico: la conferma Y/N e' stata data dal runner (lo dice la riga).
    mostraRichiesta / mostraConferme: la chat le ha gia' mostrate dal vivo.
    mostraTool: False nasconde le righe dei tool e dei loro risultati (restano
    nel log); il ragionamento del modello e la risposta restano.
    modello: nome mostrato nel prompt; se manca si usa il primo modello che ha
    risposto nel log (con il fallback puo' non essere quello preferito); se non
    c'e' nemmeno quello il prompt e' solo ">".
    """
    if not modello:
        modello = next((e["modello"] for e in eventi
                        if e.get("event") == "risposta" and e.get("modello")), "")
    righe = []
    if mostraRichiesta:
        righe.append(("prompt", f"{modello}> {richiesta}" if modello
                                              else f"> {richiesta}"))

    for e in eventi:
        tipo = e.get("event")
        if tipo == "risposta" and e.get("testo") and e.get("toolCalls"):
            # testo scritto dal modello prima di chiamare un tool: il suo "ragionamento"
            pensiero, resto = separaPensiero(e["testo"])
            if pensiero:
                righe.append(("pensiero", f"✻ {pensiero}"))
            if resto:
                righe.append(("ragiona", f"● {_inUnaRiga(resto, 400)}"))
        elif tipo == "tool_chiamato" and mostraTool:
            righe.append(("tool", "● " + formattaChiamata(e.get("tool"),
                                                         e.get("argomenti"))))
        elif tipo == "conferma" and mostraConferme:
            coda = " (automatico)" if automatico else ""
            righe.append(("conferma",
                          f"  [CONFERMA] {e.get('domanda', '')} [Y/N] {e['esito']}{coda}"))
        elif tipo == "risultato" and mostraTool:
            esito = e.get("esito", "")
            stile = "risultato" if esito == "riuscito" else "errore"
            righe.append((stile, f"  ⎿ {esito}: {_inUnaRiga(e.get('risultato', ''))}"))

    pensiero, risposta = separaPensiero(result.testoFinale)
    righe.append(("", ""))
    if pensiero:
        righe.append(("pensiero", f"✻ {pensiero}"))
        righe.append(("", ""))
    righe.append(("risposta", f"● {risposta or '(nessun testo finale)'}"))
    righe.append(("", ""))
    righe.append(("riepilogo", formatSummary(result)))
    return righe


def testoDa(righe):
    return "\n".join(testo for _, testo in righe) + "\n"
