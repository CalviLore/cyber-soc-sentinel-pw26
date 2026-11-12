# Riepilogo — 2026-11-06-gemini-3.6-flash

Esiti: fallito 2, passato 1

| # | Scenario | Run | Esito | Giri | Token | Secondi | Modelli |
|---|---|---|---|---|---|---|---|
| 1 | Routine, nessuna azione | 1 | passato | 7 | 26831 | 77.3 | gemini-3.6-flash, gemma-4-31b-it |
| 2 | Scrittura approvata (Y) | 1 | fallito | 2 | 5766 | 89.4 | gemini-3.6-flash |
| 3 | Scrittura negata (N) | 1 | fallito | 2 | 5690 | 21.5 | gemini-3.6-flash |

## Token medi per scenario

| # | Scenario | Run | Token medi |
|---|---|---|---|
| 1 | Routine, nessuna azione | 1 | 26831 |
| 2 | Scrittura approvata (Y) | 1 | 5766 |
| 3 | Scrittura negata (N) | 1 | 5690 |

## Controlli non superati

- Scenario 2 run 1: isolato solo l'IP del brute force ([])
- Scenario 2 run 1: conferma Y registrata ([])
- Scenario 3 run 1: conferma N registrata ([])
- Scenario 3 run 1: isolateIp proposto una sola volta (nessun nuovo tentativo) (0 chiamate)
