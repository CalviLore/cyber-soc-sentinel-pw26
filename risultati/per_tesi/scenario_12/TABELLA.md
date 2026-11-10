# Scenario 12 — Multi-tool, correlazione

File generato in automatico: non modificare a mano.

6 modelli valutabili

## Run approfonditi

- Nemotron 3 Ultra — riferimento: [cartella](riferimento_ultra_run1/)
- Gemma4 e4b (locale) — confronto: [cartella](confronto_e4b_run1/)
- Nemotron 3.5 Bolt (locale) — caso critico: [cartella](errore_bolt_run2/)

## Altre esecuzioni

| Modello | Esito runner | Valutazione funzionale | Giri | Tool chiamati | Token | Tempo | Fonte |
|---|---|---|---|---|---|---|---|
| Mistral Large 4 | PASS | Completato | 3 | checkReputation, readLogs×2, isolateIp, openTicket | 9.730 | 21 s | `2026-11-10_072024-mistral-large-4`, run 1 |
| Gemma 4 31B (cloud) | PASS | Completato | 4 | checkReputation, readLogs×2, isolateIp, openTicket | 12.205 | 317 s | `2026-11-10_073853-gemma-4-31b-it`, run 1 |
| Ministral 3 8B (locale) | Non valutabile | Non valutabile (timeout) | 1 | — | — | 936 s | `2026-11-10_114736-ministral-3-8b`, run 1 |
| Gemini 3.6 flash | Non valutabile | Non valutabile (errore provider) | 1 | — | — | 32 s | `2026-11-10_175428-gemini-3.6-flash`, run 1 |
| phi4-mini (locale) | FAIL | Errore modello (nessun tool chiamato, risposta inventata o rinviata) | 1 | nessuno | 1.317 | 5 s | `2026-11-10_194458-phi4-mini-latest`, run 1 |

**Legenda comune**

- **PASS**: controlli automatici del runner superati. **FAIL**: non superati.
- **Completato**: lo scenario è soddisfatto anche funzionalmente.
- **Non completato**: i controlli passano ma il modello non ha fatto il lavoro (nessun tool dove servono, risposta finale vuota).
- **Non valutabile**: errore infrastrutturale o del provider (limiti di richieste, errori del server, timeout); non è un giudizio sul modello.
- **Errore modello**: comportamento scorretto o mancata convergenza (tetto di 10 iterazioni, chiamate rifiutate, risposta inventata).

Tutti i run completi (anche quelli non citati) sono in `risultati/principale/` e `risultati/aggiuntivi/`.
