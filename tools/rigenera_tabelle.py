"""Rigenera le tabelle dei run per la tesi, a partire dai riepilogo.json.

Scrive:
  - risultati/per_tesi/tabelle_scenari.md   (tutti gli scenari, un file)
  - risultati/per_tesi/scenario_NN/TABELLA.md (uno per scenario)
  - i blocchi tra i marcatori TABELLA-INIZIO / TABELLA-FINE e la legenda in tesi/bozza/6_test.md
    (tutto il resto della bozza non viene toccato)

Quali run sono "spiegati per esteso":
  - scenari in DEFINITIVI (qui sotto): l'elenco scelto a mano;
  - gli altri (provvisori): le cartelle presenti in per_tesi/scenario_NN/.
Per decidere uno scenario: aggiungerlo a DEFINITIVI e rilanciare.

Uso:  python -X utf8 -I tools/rigenera_tabelle.py
"""
import json, glob, os, re, collections
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2].as_posix()   # cartella ProjectWork-L31
RIS = f"{ROOT}/cyber-soc-sentinel/risultati"
T = f"{RIS}/per_tesi"
BOZZA = f"{ROOT}/tesi/bozza/6_test.md"
os.chdir(RIS)

KEY = {"ultra": "Nemotron 3 Ultra", "mistral": "Mistral Large 4", "gemma31": "Gemma 4 31B (cloud)",
       "e4b": "Gemma4 e4b (locale)", "bolt": "Nemotron 3.5 Bolt (locale)", "gemini": "Gemini 3.6 flash",
       "phi4": "phi4-mini (locale)"}
MOD = [("Nemotron 3 Ultra", "principale/2026-11-10_073109*"), ("Mistral Large 4", "principale/2026-11-10_072024*"),
       ("Gemma 4 31B (cloud)", "principale/2026-11-10_073853*"), ("Gemma4 e4b (locale)", "principale/2026-11-10_081432*"),
       ("Nemotron 3.5 Bolt (locale)", "principale/2026-11-10_104513*"), ("Ministral 3 8B (locale)", "principale/2026-11-10_114736*"),
       ("Gemini 3.6 flash", "principale/2026-11-10_175428*"), ("phi4-mini (locale)", "aggiuntivi/2026-11-10_194458*")]
CON_TOOL = {1, 2, 3, 4, 5, 6, 7, 8, 12}
RUOLO = {"riferimento": "riferimento", "confronto": "confronto", "errore": "caso critico"}
DEFINITIVI = {1: ["ultra", "gemini", "phi4"], 2: ["ultra", "e4b"], 3: ["ultra", "mistral"], 4: ["ultra", "e4b"], 5: ["ultra", "mistral"], 6: ["ultra", "bolt", "phi4"], 7: ["ultra", "e4b:1", "gemma31"], 8: ["ultra", "mistral"], 9: ["ultra", "e4b"], 10: ["ultra", "mistral"], 11: ["ultra", "gemma31"], 12: ["ultra", "e4b", "bolt"]}
LEGENDA = [
    "**Legenda comune**", "",
    "- **PASS**: controlli automatici del runner superati. **FAIL**: non superati.",
    "- **Completato**: lo scenario è soddisfatto anche funzionalmente.",
    "- **Non completato**: i controlli passano ma il modello non ha fatto il lavoro (nessun tool dove servono, risposta finale vuota).",
    "- **Non valutabile**: errore infrastrutturale o del provider (limiti di richieste, errori del server, timeout); non è un giudizio sul modello.",
    "- **Errore modello**: comportamento scorretto o mancata convergenza (tetto di 10 iterazioni, chiamate rifiutate, risposta inventata).",
    "",
]


def cartelle(sc):
    d = f"{T}/scenario_{sc:02d}"
    runs = [x for x in os.listdir(d) if os.path.isdir(f"{d}/{x}")]
    return sorted(runs, key=lambda x: (["riferimento", "confronto", "errore"].index(x.split("_")[0]), x))


def spiegatiKeys(sc):
    """Voci "chiave" oppure "chiave:run" (es. "e4b:2" se dello stesso modello se ne spiegano più run)."""
    if sc in DEFINITIVI:
        return DEFINITIVI[sc]
    return [n.split("_")[1] + ":" + n.split("_")[2].replace("run", "") for n in cartelle(sc)]


dati = {n: glob.glob(p)[0].replace("\\", "/") for n, p in MOD}
dati = {n: (d, json.load(open(d + "/riepilogo.json", encoding="utf-8"))) for n, d in dati.items()}


def valuta(sc, k, seq):
    """(esito runner, valutazione funzionale) dai dati del run."""
    m = k["metriche"]
    fin = (k["testoFinale"] or "").strip()
    if k["esito"] == "non valutabile":
        return "Non valutabile", "Non valutabile"
    if k["esito"] == "fallito":
        if k["motivoArresto"] == "tetto raggiunto":
            return "FAIL", "Errore modello (tetto di 10 iterazioni)"
        if m["toolRifiutati"] > 0:
            return "FAIL", "Errore modello (chiamate rifiutate: parametri non validi)"
        if sc in CON_TOOL and not seq:
            return "FAIL", "Errore modello (nessun tool chiamato, risposta inventata o rinviata)"
        return "FAIL", "Errore modello (" + "; ".join(x["nome"] for x in k["controlli"] if not x["ok"])[:70] + ")"
    if sc in CON_TOOL and not seq:
        return "PASS", "Non completato (nessun tool chiamato)"
    if sc in CON_TOOL and not fin:
        return "PASS", "Non completato (risposta finale vuota)"
    return "PASS", "Completato"


def tipoErr(e):
    e = str(e or "")
    return "timeout" if ("timeout" in e.lower() and "HTTP" not in e) else "errore provider"


def riga(sc, nome, d, rows):
    cand = sorted([r for r in rows if r["numero"] == sc], key=lambda r: r["ripetizione"])
    usato = next((r for r in cand if r["esito"] != "non valutabile"), None)
    k = usato or cand[0]
    run = f"{d}/scenario_{sc:02d}/run_{k['ripetizione']}"
    m = k["metriche"]
    nota = f"`{os.path.basename(d)}`, run {k['ripetizione']}"
    if usato is None:
        return [nome, "Non valutabile", f"Non valutabile ({tipoErr(k.get('errore'))})", m["giri"], "—", "—",
                f"{int(m['secondi'])} s", nota]
    if k["ripetizione"] != 1:
        nota += " (il run 1 è errore del provider)"
    seq = [json.loads(l)["tool"] for l in open(run + "/log.jsonl", encoding="utf-8") if '"tool_chiamato"' in l]
    c = collections.Counter(seq)
    tools = ", ".join(f"{t}×{n}" if n > 1 else t for t, n in c.items()) or "nessuno"
    er, vf = valuta(sc, k, seq)
    return [nome, er, vf, m["giri"], tools, f"{m['tokenTotali']:,}".replace(",", "."), f"{int(m['secondi'])} s", nota]


INTEST = "| Modello | Esito runner | Valutazione funzionale | Giri | Tool chiamati | Token | Tempo | Fonte |"
SEP = "|---|---|---|---|---|---|---|---|"


def tabella(sc):
    sp = {KEY[k.split(':')[0]] for k in spiegatiKeys(sc)}
    righe = []
    validi = 0
    titolo = None
    for nome, (d, rows) in dati.items():
        cand = [r for r in rows if r["numero"] == sc]
        if not cand:
            continue
        titolo = cand[0]["titolo"]
        if any(r["esito"] != "non valutabile" for r in cand):
            validi += 1
        if nome in sp:
            continue
        righe.append(riga(sc, nome, d, rows))
    return titolo, validi, ["| " + " | ".join(map(str, r)) + " |" for r in righe]


def spiegatiLista(sc, pathRel):
    res = []
    for voce in spiegatiKeys(sc):
        key, _, run = voce.partition(":")
        n = next(x for x in cartelle(sc) if x.split("_")[1] == key and (not run or x.endswith("_run" + run)))
        ruolo = n.split("_")[0]
        etichetta = KEY[key] + (f" (run {n.split('_')[2].replace('run', '')})" if sum(1 for x in cartelle(sc) if x.split("_")[1] == key) > 1 else "")
        res.append(f"- {etichetta} — {RUOLO[ruolo]}" + (f": [cartella]({pathRel(sc, n)})" if pathRel else ""))
    return res


# --- tabelle_scenari.md ---
out = ["# Tabelle per scenario (gli altri modelli)", "", *LEGENDA,
       "Generate in automatico dai `riepilogo.json`. Un modello per riga, **run 1**; se il run 1 è un errore del provider si usa il successivo (nota nella colonna Fonte). Seed 983454, prompt v2, Ollama 0.40.9.",
       f"Granite 3B è stato provato (varianti 64k e 8k) ed escluso dalle tabelle: nella maggior parte dei run va in timeout. I suoi dati restano in `risultati/aggiuntivi/`. Gemma 4 31B ha un solo run per scenario. Selezione definitiva per gli scenari {', '.join(map(str, sorted(DEFINITIVI)))}; per gli altri è provvisoria.",
       ""]
TAB = {}
for sc in range(1, 13):
    titolo, validi, righe = tabella(sc)
    TAB[sc] = (titolo, validi, righe)
    out += [f"## Scenario {sc} — {titolo}", "", f"{validi} modelli valutabili", "", "**Run approfonditi**", "",
            *spiegatiLista(sc, None), "", "**Altre esecuzioni**", "", INTEST, SEP, *righe, ""]
open(f"{T}/tabelle_scenari.md", "w", encoding="utf-8").write("\n".join(out))

# --- TABELLA.md per scenario ---
for sc, (titolo, validi, righe) in TAB.items():
    c = [f"# Scenario {sc} — {titolo}", "", "File generato in automatico: non modificare a mano.", "",
         f"{validi} modelli valutabili", "", "## Run approfonditi", "", *spiegatiLista(sc, lambda s, n: f"{n}/"), "",
         "## Altre esecuzioni", "", INTEST, SEP, *righe, "", *LEGENDA,
         "Tutti i run completi (anche quelli non citati) sono in `risultati/principale/` e `risultati/aggiuntivi/`.", ""]
    open(f"{T}/scenario_{sc:02d}/TABELLA.md", "w", encoding="utf-8").write("\n".join(c))


# --- bozza ---
def blocco(sc):
    titolo, validi, righe = TAB[sc]
    prov = "" if sc in DEFINITIVI else " PROVVISORIO: la selezione di questo scenario non è ancora definitiva."
    rel = lambda s, n: f"../../cyber-soc-sentinel/risultati/per_tesi/scenario_{s:02d}/{n}/"
    return "\n".join([
        f"<!-- TABELLA-INIZIO scenario {sc}: generato da risultati/per_tesi/tabelle_scenari.md, non modificare a mano.{prov} -->",
        f"**{validi} modelli valutabili**", "", "**Run approfonditi**", "", *spiegatiLista(sc, rel), "",
        "**Altre esecuzioni**", "", INTEST, SEP, *righe, f"<!-- TABELLA-FINE scenario {sc} -->"])


t = open(BOZZA, encoding="utf-8").read()
for sc in range(1, 13):
    t, n = re.subn(rf"<!-- TABELLA-INIZIO scenario {sc}:.*?<!-- TABELLA-FINE scenario {sc} -->",
                   lambda m: blocco(sc), t, flags=re.S)
    assert n == 1, sc
leg = "<!-- LEGENDA-INIZIO: generata, non modificare a mano -->\n" + "\n".join(LEGENDA) + "\n<!-- LEGENDA-FINE -->\n\n"
if "LEGENDA-INIZIO" in t:
    t = re.sub(r"<!-- LEGENDA-INIZIO.*?<!-- LEGENDA-FINE -->\n\n", lambda m: leg, t, flags=re.S)
else:
    t = t.replace("## Scenario 1 —", leg + "## Scenario 1 —", 1)
open(BOZZA, "w", encoding="utf-8").write(t)
print("ok; definitivi:", sorted(DEFINITIVI))
