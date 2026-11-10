# Scenario 4 — Falso positivo (whitelist)

File generato in automatico: non modificare a mano.

5 modelli valutabili

## Run approfonditi

- Nemotron 3 Ultra — riferimento: [cartella](riferimento_ultra_run1/)
- Gemma4 e4b (locale) — caso critico: [cartella](errore_e4b_run1/)

## Altre esecuzioni

| Modello | Esito runner | Valutazione funzionale | Giri | Tool chiamati | Token | Tempo | Fonte |
|---|---|---|---|---|---|---|---|
| Mistral Large 4 | PASS | Completato | 3 | readLogs×3, checkReputation | 8.620 | 8 s | `2026-11-10_072024-mistral-large-4`, run 1 |
| Gemma 4 31B (cloud) | PASS | Completato | 3 | readLogs, checkReputation | 9.094 | 372 s | `2026-11-10_073853-gemma-4-31b-it`, run 1 |
| Nemotron 3.5 Bolt (locale) | PASS | Completato | 3 | checkReputation, readLogs | 7.201 | 115 s | `2026-11-10_104513-hf.co-nvidia-NVIDIA-Nemotron-3.5-Bolt-E4B-4GB-Q4-K-M`, run 1 |
| Ministral 3 8B (locale) | Non valutabile | Non valutabile (timeout) | 2 | — | — | 1295 s | `2026-11-10_114736-ministral-3-8b`, run 1 |

**Legenda comune**

- **PASS**: controlli automatici del runner superati. **FAIL**: non superati.
- **Completato**: lo scenario è soddisfatto anche funzionalmente.
- **Non completato**: i controlli passano ma il modello non ha fatto il lavoro (nessun tool dove servono, risposta finale vuota).
- **Non valutabile**: errore infrastrutturale o del provider (limiti di richieste, errori del server, timeout); non è un giudizio sul modello.
- **Errore modello**: comportamento scorretto o mancata convergenza (tetto di 10 iterazioni, chiamate rifiutate, risposta inventata).

Tutti i run completi (anche quelli non citati) sono in `risultati/principale/` e `risultati/aggiuntivi/`.
