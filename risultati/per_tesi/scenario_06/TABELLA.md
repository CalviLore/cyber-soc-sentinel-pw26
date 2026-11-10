# Scenario 6 — Ticket da errori 500

File generato in automatico: non modificare a mano.

6 modelli valutabili

## Run approfonditi

- Nemotron 3 Ultra — riferimento: [cartella](riferimento_ultra_run1/)
- Nemotron 3.5 Bolt (locale) — caso critico: [cartella](errore_bolt_run2/)
- phi4-mini (locale) — caso critico: [cartella](errore_phi4_run1/)

## Altre esecuzioni

| Modello | Esito runner | Valutazione funzionale | Giri | Tool chiamati | Token | Tempo | Fonte |
|---|---|---|---|---|---|---|---|
| Mistral Large 4 | PASS | Completato | 3 | readLogs, openTicket | 6.425 | 11 s | `2026-11-10_072024-mistral-large-4`, run 1 |
| Gemma 4 31B (cloud) | PASS | Completato | 3 | readLogs, openTicket | 6.280 | 195 s | `2026-11-10_073853-gemma-4-31b-it`, run 1 |
| Gemma4 e4b (locale) | PASS | Completato | 3 | readLogs, openTicket | 6.650 | 255 s | `2026-11-10_081432-gemma4-e4b`, run 1 |
| Ministral 3 8B (locale) | Non valutabile | Non valutabile (timeout) | 2 | — | — | 1014 s | `2026-11-10_114736-ministral-3-8b`, run 1 |

**Legenda comune**

- **PASS**: controlli automatici del runner superati. **FAIL**: non superati.
- **Completato**: lo scenario è soddisfatto anche funzionalmente.
- **Non completato**: i controlli passano ma il modello non ha fatto il lavoro (nessun tool dove servono, risposta finale vuota).
- **Non valutabile**: errore infrastrutturale o del provider (limiti di richieste, errori del server, timeout); non è un giudizio sul modello.
- **Errore modello**: comportamento scorretto o mancata convergenza (tetto di 10 iterazioni, chiamate rifiutate, risposta inventata).

Tutti i run completi (anche quelli non citati) sono in `risultati/principale/` e `risultati/aggiuntivi/`.
