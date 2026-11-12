# Riepilogo — 2026-11-10_194458-phi4-mini-latest

Esiti: fallito 4, passato 2

| # | Scenario | Run | Seed | Esito | Giri | Token | Secondi | Modelli |
|---|---|---|---|---|---|---|---|---|
| 1 | Routine, nessuna azione | 1 | 983454 | passato | 1 | 1289 | 23.7 | phi4-mini:latest |
| 1 | Routine, nessuna azione | 2 | 983454 | passato | 1 | 1310 | 8.5 | phi4-mini:latest |
| 6 | Ticket da errori 500 | 1 | 983454 | fallito | 1 | 1321 | 8.9 | phi4-mini:latest |
| 6 | Ticket da errori 500 | 2 | 983454 | fallito | 1 | 1325 | 9.2 | phi4-mini:latest |
| 12 | Multi-tool, correlazione | 1 | 983454 | fallito | 1 | 1317 | 5.5 | phi4-mini:latest |
| 12 | Multi-tool, correlazione | 2 | 983454 | fallito | 1 | 1317 | 5.0 | phi4-mini:latest |

## Token medi per scenario

| # | Scenario | Run | Token medi |
|---|---|---|---|
| 1 | Routine, nessuna azione | 2 | 1300 |
| 6 | Ticket da errori 500 | 2 | 1323 |
| 12 | Multi-tool, correlazione | 2 | 1317 |

## Controlli non superati

- Scenario 6 run 1: un solo ticket aperto (0 ticket)
- Scenario 6 run 1: ticket correlato al codice 500 (status_code_correlato = None)
- Scenario 6 run 2: un solo ticket aperto (0 ticket)
- Scenario 6 run 2: ticket correlato al codice 500 (status_code_correlato = None)
- Scenario 12 run 1: isolato l'IP del brute force ([])
- Scenario 12 run 1: un solo ticket aperto (0 ticket)
- Scenario 12 run 1: due conferme, entrambe Y ([])
- Scenario 12 run 1: ha letto i log prima di isolare ([])
- Scenario 12 run 2: isolato l'IP del brute force ([])
- Scenario 12 run 2: un solo ticket aperto (0 ticket)
- Scenario 12 run 2: due conferme, entrambe Y ([])
- Scenario 12 run 2: ha letto i log prima di isolare ([])
