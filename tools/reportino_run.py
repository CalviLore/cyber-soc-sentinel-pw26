"""Genera risultati/per_tesi/REPORTINO.md: sintesi dei run spiegati per esteso.

Legge le cartelle scenario_NN/<ruolo>_<modello>_run<K>/ di risultati/per_tesi/ e, per ogni run,
riporta esito, giri, token, tempo, sequenza dei tool, controlli non superati e l'inizio della risposta.
Le tabelle degli altri modelli sono in tabelle_scenari.md (tools/rigenera_tabelle.py).

Uso:  python -X utf8 -I tools/reportino_run.py
"""
import json
import os
from pathlib import Path

PER_TESI = Path(__file__).resolve().parents[1] / "risultati" / "per_tesi"
ORDINE = ("riferimento", "confronto", "errore")
ETICHETTA = {"riferimento": "riferimento", "confronto": "confronto", "errore": "caso critico"}


def sintesiRun(cartella):
    s = json.load(open(cartella / "scenario.json", encoding="utf-8"))
    m = json.load(open(cartella / "metriche.json", encoding="utf-8"))
    tool = [json.loads(r)["tool"] for r in open(cartella / "log.jsonl", encoding="utf-8")
            if '"tool_chiamato"' in r]
    finale = (s.get("testoFinale") or "").replace("\n", " ").strip()
    ko = [c["nome"] for c in s["controlli"] if not c["ok"]]
    righe = [f"**{cartella.name}** · {s['esito'].upper()} · {m['giri']} giri · {m['tokenTotali']} token · {int(m['secondi'])} s",
             f"- Tool: {' > '.join(tool) if tool else 'nessuno'}"]
    if ko:
        righe.append(f"- Controlli non superati: {'; '.join(ko)}")
    righe.append(f"- Risposta: {finale[:170]}{'…' if len(finale) > 170 else ''}")
    return righe + [""]


def main():
    out = ["# Reportino dei run spiegati per esteso", "",
           "Sintesi automatica da `scenario.json`, `metriche.json` e `log.jsonl` di ogni run. "
           "Selezione definitiva (12 scenari). Seed 983454, prompt v2. "
           "Gli altri modelli di ogni scenario sono in `tabelle_scenari.md`.", ""]
    for sd in sorted(d for d in os.listdir(PER_TESI) if d.startswith("scenario_")):
        runs = sorted((d for d in os.listdir(PER_TESI / sd) if (PER_TESI / sd / d).is_dir()),
                      key=lambda n: (ORDINE.index(n.split("_")[0]), n))
        sc = json.load(open(PER_TESI / sd / runs[0] / "scenario.json", encoding="utf-8"))
        out += [f"## Scenario {sc['numero']} — {sc['titolo']}",
                f"- Richiesta: «{sc['richiesta'][:140]}»", f"- Atteso: {sc['atteso']}", ""]
        for n in runs:
            out += sintesiRun(PER_TESI / sd / n)
    (PER_TESI / "REPORTINO.md").write_text("\n".join(out), encoding="utf-8")
    print("scritto", PER_TESI / "REPORTINO.md", "-", len(out), "righe")


if __name__ == "__main__":
    main()
