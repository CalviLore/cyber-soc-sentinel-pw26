# Back-end: cosa fa e dove sta

La traccia chiede "un semplice back-end con base dati relazionale popolata con
dati sintetici". Qui il back-end è lo strato che lavora sui dati aziendali:
legge e scrive il database.

## Dove si colloca

```mermaid
flowchart LR
    U([Operatore]) --> H[Harness agentico<br/>ciclo, conferma Y/N, log]
    H <--> L[Modello linguistico<br/>Ollama]
    H <--> M[Server MCP<br/>4 tool + schema]
    M --> B[Back-end<br/>src/backend.py]
    B --> D[(SQLite<br/>6 tabelle)]
    S[Simulatore<br/>tools/simulatore.py] -.popola.-> D
```

Ogni strato ha un compito solo:

| Strato | Cosa fa | Cosa non fa |
|---|---|---|
| Back-end | Esegue le operazioni sul DB, controlla che i dati siano validi, restituisce un risultato o un errore | Non conosce il modello, né MCP, né l'utente |
| Server MCP | Espone le 4 funzioni come *tool* con nome, descrizione e schema dei parametri | Non ha logica sui dati: chiama il back-end |
| Harness | Guida il ciclo con il modello, chiede conferma prima delle scritture, scrive il log | Non tocca il DB direttamente |
| Simulatore | Prepara i dati degli scenari per i test | Non fa parte del sistema in esercizio |

## Le funzioni

Sono quattro, una per tool. Ognuna riceve parametri semplici e restituisce un
dizionario (JSON), senza mai sollevare un'eccezione verso l'alto.

| Funzione | Legge/scrive | Cosa fa |
|---|---|---|
| `readLogs(ip=None, statusCode=None, limit=100)` | legge `network_logs` | Filtra i log per IP e/o codice, dal più recente, fino a `limit` righe. Restituisce `{"total": n, "returned": m, "logs": [...]}` |
| `checkReputation(ip)` | legge `ip_whitelist`, `threat_intel_db`, `assets` | Dice se l'IP è in whitelist, se è nel threat intel e con che score, e se è un asset critico |
| `isolateIp(ip, reason)` | scrive `isolated_ips` | Controlla che l'IP sia IPv4 valido e non già isolato, poi inserisce la riga. Rifiuta gli asset critici |
| `openTicket(title, description, severity, relatedIp?, relatedStatusCode?)` | scrive `incident_tickets` | Controlla che `severity` sia Bassa/Media/Alta, poi inserisce il ticket |

## Le regole che il back-end fa rispettare

Stanno qui e non nel modello perché devono valere anche quando il modello
sbaglia.

- **IP non valido** (per esempio `999.999`): risponde `{"error": "Invalid IP"}` e non scrive nulla.
- **IP già isolato**: risponde `{"error": "IP already isolated"}`.
- **Asset critico** (host amministrativo, server dell'agente SOC): non si isola
  mai, nemmeno se un testo iniettato nei log lo chiede (scenario 7). Il back-end
  risponde con un errore che nomina l'asset (`Critical asset (...): cannot be
  isolated`) e l'harness registra comunque il tentativo nel log. L'IP
  dell'agente sta in `assets` con `critico = 1`, quindi non può isolare sé
  stesso e non serve codice speciale. La whitelist riguarda altro: il traffico
  legittimo e i falsi positivi.
- **Gravità fuori elenco**: risponde `{"error": "Invalid severity (use one of: Bassa, Media, Alta)"}`.
- **Nessun dato trovato**: restituisce `total: 0`, mai un valore plausibile.

## Cosa spetta ad altri

- **La conferma Y/N** è dell'harness. Il back-end esegue quando viene chiamato;
  decidere se chiamarlo dopo il "sì" dell'utente tocca all'harness.
- **Decidere cos'è un attacco** spetta al modello. Il back-end restituisce
  fatti (50 login falliti) e nessun giudizio.
- **La validazione dello schema JSON dei parametri** la fa l'harness prima di
  chiamare il server (scenario 9). Il back-end ripete i controlli essenziali
  come seconda difesa.

## Perché separarlo dal server MCP

1. La traccia lo chiama "back-end", quindi va consegnato e descritto come
   codice a sé.
2. Si testa da solo: basta una funzione su un DB di prova, senza MCP né modello.
3. Il server MCP resta sottile. Ogni tool è poche righe che chiamano il
   back-end, e questo rende facile spiegarlo nel report ("almeno un tool").

## Esempio di flusso (scenario 2)

1. L'operatore scrive: "Controlla l'IP X: ha fatto molti accessi falliti?"
2. Il modello chiede `readLogs(ip=X, statusCode=401)`. L'harness inoltra la
   richiesta al server MCP, che chiama `backend.readLogs(...)` e risponde con
   50 log.
3. Il modello propone `isolateIp`. L'harness chiede Y/N e l'operatore digita Y.
4. Il server MCP chiama `backend.isolateIp(X, reason)`, che inserisce la riga
   in `isolated_ips`.
5. Il modello conferma all'operatore. Ogni passo finisce nel log JSONL.
