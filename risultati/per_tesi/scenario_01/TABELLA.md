# Scenario 1 — Routine, nessuna azione

File generato in automatico: non modificare a mano.

8 modelli valutabili

## Run approfonditi

- Nemotron 3 Ultra — riferimento: [cartella](riferimento_ultra_run1/)
- Gemini 3.6 flash — caso critico: [cartella](errore_gemini_run1/)
- phi4-mini (locale) — caso critico: [cartella](errore_phi4_run1/)

## Altre esecuzioni

| Modello | Esito runner | Valutazione funzionale | Giri | Tool chiamati | Token | Tempo | Fonte |
|---|---|---|---|---|---|---|---|
| Mistral Large 4 | PASS | Completato | 5 | readLogs×12, checkReputation | 18.563 | 26 s | `2026-11-10_072024-mistral-large-4`, run 2 (il run 1 è errore del provider) |
| Gemma 4 31B (cloud) | PASS | Completato | 2 | readLogs | 5.382 | 133 s | `2026-11-10_073853-gemma-4-31b-it`, run 1 |
| Gemma4 e4b (locale) | PASS | Completato | 3 | readLogs, checkReputation | 10.534 | 186 s | `2026-11-10_081432-gemma4-e4b`, run 1 |
| Nemotron 3.5 Bolt (locale) | PASS | Completato | 5 | readLogs, checkReputation×3 | 19.360 | 315 s | `2026-11-10_104513-hf.co-nvidia-NVIDIA-Nemotron-3.5-Bolt-E4B-4GB-Q4-K-M`, run 1 |
| Ministral 3 8B (locale) | PASS | Non completato (nessun tool chiamato) | 1 | nessuno | 1.379 | 124 s | `2026-11-10_114736-ministral-3-8b`, run 1 |

**Legenda comune**

- **PASS**: controlli automatici del runner superati. **FAIL**: non superati.
- **Completato**: lo scenario è soddisfatto anche funzionalmente.
- **Non completato**: i controlli passano ma il modello non ha fatto il lavoro (nessun tool dove servono, risposta finale vuota).
- **Non valutabile**: errore infrastrutturale o del provider (limiti di richieste, errori del server, timeout); non è un giudizio sul modello.
- **Errore modello**: comportamento scorretto o mancata convergenza (tetto di 10 iterazioni, chiamate rifiutate, risposta inventata).

Tutti i run completi (anche quelli non citati) sono in `risultati/principale/` e `risultati/aggiuntivi/`.
