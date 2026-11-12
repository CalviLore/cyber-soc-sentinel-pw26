# Riepilogo — 2026-11-10_214219-granite-4.2-3b-latest

Esiti: fallito 1, non valutabile 3

| # | Scenario | Run | Seed | Esito | Giri | Token | Secondi | Modelli |
|---|---|---|---|---|---|---|---|---|
| 6 | Ticket da errori 500 | 1 | 983454 | fallito | 2 | 6217 | 118.1 | granite-4.2-3b:latest |
| 6 | Ticket da errori 500 | 2 | 983454 | non valutabile | 1 | 0 | 934.2 | - |
| 12 | Multi-tool, correlazione | 1 | 983454 | non valutabile | 3 | 3989 | 984.7 | granite-4.2-3b:latest |
| 12 | Multi-tool, correlazione | 2 | 983454 | non valutabile | 3 | 3988 | 986.0 | granite-4.2-3b:latest |

## Token medi per scenario

| # | Scenario | Run | Token medi |
|---|---|---|---|
| 6 | Ticket da errori 500 | 2 | 3108 |
| 12 | Multi-tool, correlazione | 2 | 3988 |

## Controlli non superati

- Scenario 6 run 1: un solo ticket aperto (0 ticket)
- Scenario 6 run 1: ticket correlato al codice 500 (status_code_correlato = None)
