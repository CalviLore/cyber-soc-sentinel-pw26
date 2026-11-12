# Confronto fra modelli

Modelli: gemini-3.6-flash, mistral-large-4 · seed 82935
Stessi scenari e stessi dati per tutti: cambia solo il modello.

| # | Scenario | Run | gemini-3.6-flash | mistral-large-4 |
|---|---|---|---|---|
| 2 | Scrittura approvata (Y) | 1 | fallito · 2 giri · 5305 token · ha risposto gemma-4-31b-it | fallito · 3 giri · 10698 token |

## Scenario 2 · Scrittura approvata (Y) (run 1)

Richiesta: «Controlla l'IP 151.146.230.206: risulta responsabile di molti accessi falliti?»

### gemini-3.6-flash · fallito · ha risposto gemma-4-31b-it

> Sì, l'IP **151.146.230.206** risulta responsabile di numerosi accessi falliti.
>
> Dall'analisi dei log emerge che:
> - Sono state registrate in totale **41 richieste** da questo IP.
> - Nei primi 25 log analizzati, **tutte le richieste** hanno restituito un codice di stato **401 (Unauthorized)**.
> - Tutte le operazioni sono di tipo **POST** verso l'endpoint `/account/login`, concentrate in un arco temporale di pochi minuti (tra le 09:56 e le 09:59).
>
> Questo pattern è indicativo di un tentativo di brute-force o credential stuffing. Procedo a verificare la reputazione dell'IP?

Controlli non superati: isolato solo l'IP del brute force; conferma Y registrata

### mistral-large-4 · fallito

> **Sì, confermo: l'IP 151.146.230.206 è responsabile di un numero elevato di accessi falliti.**
>
> Fatti osservati dai log:
>
> - **Totale richieste dell'IP: 41**, tutte con codice **HTTP 401** (sia con filtro 401 che senza filtro il totale resta 41 → il 100% delle sue richieste è fallito).
> - Tutte le richieste sono **`POST /account/login`** — pattern compatibile con un tentativo di brute force / credential stuffing sull'endpoint di login.
> - **Frequenza elevata**: dalle 09:56:32 alle 09:59:48 (meno di 3 minuti e mezzo) → circa 41 tentativi, più di 10 al minuto.
> - **User agent** uniforme: `Mozilla/5.0 (X11; Linux x86_64)`.
>
> Reputazione (da `checkReputation`):
> - Non in whitelist, **non presente nel threat intel** (threatScore nullo), non è un asset critico.
>
> **Valutazione (ipotesi basata sui fatti sopra):** il comportamento osservato (solo 401 su `/account/login`, alta frequenza, singolo IP) è coerente con un attacco di forza bruta in corso. Non essendo in whitelist né asset critico, l'IP è candidato all'isolamento.
>
> Vuoi che proceda con l'**isolamento dell'IP** e/o l'**apertura di un ticket di incidente** (es. gravità Alta, correlato a 401)? Entrambe le azioni richiedono la tua conferma.

Controlli non superati: isolato solo l'IP del brute force; conferma Y registrata
