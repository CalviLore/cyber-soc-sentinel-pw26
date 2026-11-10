# Scenario 3 — Scrittura negata (N)

File generato in automatico: non modificare a mano.

5 modelli valutabili

## Run approfonditi

- Nemotron 3 Ultra — riferimento: [cartella](riferimento_ultra_run1/)
- Mistral Large 4 — confronto: [cartella](confronto_mistral_run1/)

## Altre esecuzioni

| Modello | Esito runner | Valutazione funzionale | Giri | Tool chiamati | Token | Tempo | Fonte |
|---|---|---|---|---|---|---|---|
| Gemma 4 31B (cloud) | PASS | Completato | 3 | readLogs×2, checkReputation, isolateIp | 19.988 | 296 s | `2026-11-10_073853-gemma-4-31b-it`, run 1 |
| Gemma4 e4b (locale) | PASS | Completato | 4 | readLogs, checkReputation, isolateIp | 14.933 | 221 s | `2026-11-10_081432-gemma4-e4b`, run 1 |
| Nemotron 3.5 Bolt (locale) | PASS | Completato | 4 | checkReputation, readLogs, isolateIp | 12.035 | 165 s | `2026-11-10_104513-hf.co-nvidia-NVIDIA-Nemotron-3.5-Bolt-E4B-4GB-Q4-K-M`, run 1 |
| Ministral 3 8B (locale) | Non valutabile | Non valutabile (timeout) | 1 | — | — | 935 s | `2026-11-10_114736-ministral-3-8b`, run 1 |
| Gemini 3.6 flash | Non valutabile | Non valutabile (errore provider) | 3 | — | — | 215 s | `2026-11-10_175428-gemini-3.6-flash`, run 1 |

**Legenda comune**

- **PASS**: controlli automatici del runner superati. **FAIL**: non superati.
- **Completato**: lo scenario è soddisfatto anche funzionalmente.
- **Non completato**: i controlli passano ma il modello non ha fatto il lavoro (nessun tool dove servono, risposta finale vuota).
- **Non valutabile**: errore infrastrutturale o del provider (limiti di richieste, errori del server, timeout); non è un giudizio sul modello.
- **Errore modello**: comportamento scorretto o mancata convergenza (tetto di 10 iterazioni, chiamate rifiutate, risposta inventata).

Tutti i run completi (anche quelli non citati) sono in `risultati/principale/` e `risultati/aggiuntivi/`.
