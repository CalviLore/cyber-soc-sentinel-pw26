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
import textwrap
from datetime import datetime

from agent import formatSummary
from llm.pensiero import separaPensiero  # noqa: F401 (usato anche dai test)

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


def _blocchiPensiero(pensiero, semplice):
    """Righe del pensiero: stile Ollama (Thinking... / ...done thinking.) oppure con ✻."""
    if not pensiero:
        return []
    if semplice:
        return [("pensiero", "Thinking..."), ("pensiero", pensiero),
                ("pensiero", "...done thinking."), ("", "")]
    return [("pensiero", f"✻ {pensiero}"), ("", "")]


def righeSessione(richiesta, eventi, result, *, modello=None, automatico=True,
                  mostraRichiesta=True, mostraConferme=True, mostraTool=True,
                  mostraRiepilogo=True, semplice=False):
    """Lista di (stile, testo). Stili: prompt, tool, conferma, risultato,
    errore, ragiona, pensiero, risposta, riepilogo.

    automatico: la conferma Y/N e' stata data dal runner (lo dice la riga).
    mostraRichiesta / mostraConferme: la chat le ha gia' mostrate dal vivo.
    mostraTool: False nasconde le righe dei tool e dei loro risultati (restano
    nel log); il ragionamento del modello e la risposta restano.
    mostraRiepilogo: False toglie la riga grigia sotto la risposta (arresto,
    giri, token): i numeri restano in metriche.json.
    semplice: stile sobrio come la CLI di Ollama: prompt ">>> domanda", pensiero
    grigio tra "Thinking..." e "...done thinking.", risposta senza pallino. In
    questo stile il nome del modello non sta nel prompt (lo mette l'immagine nella
    barra del titolo).
    modello: nome mostrato nel prompt (stile completo); se manca si usa il primo
    modello che ha risposto nel log (con il fallback puo' non essere quello
    preferito); se non c'e' nemmeno quello il prompt e' solo ">".
    """
    if not modello:
        modello = next((e["modello"] for e in eventi
                        if e.get("event") == "risposta" and e.get("modello")), "")
    righe = []
    if mostraRichiesta:
        if semplice:
            righe.append(("prompt", f">>> {richiesta}"))
        else:
            righe.append(("prompt", f"{modello}> {richiesta}" if modello
                                    else f"> {richiesta}"))

    posPensiero = len(righe)  # nello stile semplice il pensiero va subito dopo la domanda
    raccolti = []             # note del modello, nell'ordine in cui le ha scritte

    for e in eventi:
        tipo = e.get("event")
        if tipo == "risposta":
            # ragionamento esposto dal modello (campo pensiero del log) e, se scrive
            # del testo prima di chiamare un tool, quella nota
            pensiero = e.get("pensiero") or ""
            nota = e.get("testo") if e.get("toolCalls") else None
            if nota:  # log vecchi: pensiero scritto tra tag dentro il testo
                tag, nota = separaPensiero(nota)
                pensiero = "\n\n".join(p for p in (pensiero, tag) if p)
            if semplice:
                raccolti += [x for x in (pensiero, nota) if x]
                continue
            righe += _blocchiPensiero(pensiero, semplice)
            if nota:
                righe.append(("ragiona", f"● {_inUnaRiga(nota, 400)}"))
        elif tipo == "tool_chiamato" and mostraTool:
            righe.append(("tool", "● " + formattaChiamata(e.get("tool"),
                                                         e.get("argomenti"))))
        elif tipo == "conferma" and mostraConferme:
            coda = " (automatico)" if automatico else ""
            rientro = "" if semplice else "  "
            righe.append(("conferma",
                          f"{rientro}[CONFERMA] {e.get('domanda', '')} "
                          f"[Y/N] {e['esito']}{coda}"))
        elif tipo == "risultato" and mostraTool:
            esito = e.get("esito", "")
            stile = "risultato" if esito == "riuscito" else "errore"
            righe.append((stile, f"  ⎿ {esito}: {_inUnaRiga(e.get('risultato', ''))}"))

    pensiero, risposta = separaPensiero(result.testoFinale)
    if semplice:
        # un solo blocco Thinking... con tutte le note del modello, prima di conferme e risposta
        if pensiero:
            raccolti.append(pensiero)
        righe[posPensiero:posPensiero] = _blocchiPensiero("\n".join(raccolti), True)
        righe.append(("", ""))
    else:
        righe.append(("", ""))
        righe += _blocchiPensiero(pensiero, semplice)
    testo = risposta or "(nessun testo finale)"
    righe.append(("risposta", testo if semplice else f"● {testo}"))
    if mostraRiepilogo:
        righe.append(("", ""))
        righe.append(("riepilogo", formatSummary(result)))
    return righe


def testoDa(righe):
    return "\n".join(testo for _, testo in righe) + "\n"


# ---------------------------------------------------------------------------
# Log leggibile (per le pagine del report)
# ---------------------------------------------------------------------------

LARGHEZZA_LOG = 100
RIENTRO_LOG = 28


def _ora(ts):
    """Ora locale HH:MM:SS dal timestamp ISO del log."""
    try:
        return datetime.fromisoformat(ts).astimezone().strftime("%H:%M:%S")
    except (TypeError, ValueError):
        return "--:--:--"


def _risultatoBreve(testo, limite=LIMITE_RISULTATO):
    """Risultato di un tool su una riga; per readLogs le righe di log si omettono."""
    testo = str(testo)
    if '"logs": [' in testo:  # total e returned bastano: le righe stanno nel .jsonl
        testo = testo.split('"logs": [')[0] + '"logs": […]}'
    return _inUnaRiga(testo, limite)


def _blocco(testo):
    """Testo lungo a capo, rientrato sotto la colonna dell'evento."""
    righe = []
    for originale in str(testo).splitlines():  # si tengono gli a-capo del modello
        if originale.strip():
            righe += textwrap.wrap(originale.strip(), LARGHEZZA_LOG)
    return [" " * RIENTRO_LOG + r for r in righe or [""]]


def logLeggibile(eventi):
    """Il log JSONL come testo da leggere: una riga per evento, a colonne.

        ora       giro  evento      dettaglio
        15:34:53  1     TOOL        readLogs(limit=25)

    Il log JSONL resta la fonte (completo, per le macchine); questo e' per le
    pagine del report: risultati accorciati, richieste e testi a capo.
    """
    righe = ["ora       giro  evento      dettaglio",
             "-" * (RIENTRO_LOG + LARGHEZZA_LOG)]

    def riga(e, etichetta, dettaglio):
        giro = e.get("giro", "")
        righe.append(f"{_ora(e.get('ts')):<10}{str(giro):<6}{etichetta:<12}{dettaglio}")

    for e in eventi:
        tipo = e.get("event")
        if tipo == "richiesta":
            riga(e, "RICHIESTA", f"modello {e.get('modello', '?')} · "
                                 f"{e.get('nMessaggi', '?')} messaggi")
            if e.get("richiestaUtente"):
                righe += _blocco(f"«{e['richiestaUtente']}»")
        elif tipo == "risposta":
            chiede = ", ".join(e.get("toolCalls") or [])
            parti = [f"{e.get('totalTokens', 0)} token "
                     f"({e.get('promptTokens', 0)} + {e.get('completionTokens', 0)})",
                     f"{e.get('latenzaSecondi', '?')} s", e.get("modello", "")]
            if chiede:
                parti.append(f"chiede: {chiede}")
            if e.get("toolDaTesto"):
                parti.append("TOOL LETTI DAL TESTO")
            if e.get("fallback"):
                parti.append(f"FALLBACK: {e['fallback']}")
            riga(e, "RISPOSTA", " · ".join(p for p in parti if p))
            if e.get("testo"):
                righe += _blocco(e["testo"])
        elif tipo == "tool_chiamato":
            riga(e, "TOOL", formattaChiamata(e.get("tool"), e.get("argomenti")))
        elif tipo == "conferma":
            riga(e, "CONFERMA", f"{e.get('domanda', '')} → {e.get('esito', '?')}")
        elif tipo == "risultato":
            riga(e, "RISULTATO", f"{e.get('esito', '')} · "
                                 f"{_risultatoBreve(e.get('risultato', ''))}")
        elif tipo == "fine":
            riga(e, "FINE", f"{e.get('motivo', '')} · {e.get('tokenTotali', 0)} token")
        elif tipo in ("errore_modello", "interrotto"):
            riga(e, tipo.upper().replace("_", " "), e.get("errore", ""))
        elif tipo in ("nuova_conversazione", "sessione_inizio", "sessione_fine"):
            riga(e, tipo.upper().replace("_", " "), "")
    return "\n".join(righe) + "\n"
