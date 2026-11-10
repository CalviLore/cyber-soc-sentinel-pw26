# Diagrammi UML

I diagrammi richiesti dalla traccia (PW 26), in Mermaid: si vedono su GitHub e
nell'anteprima Markdown di VS Code (`Ctrl+Shift+V`). Ogni diagramma ha il sorgente
`.mmd` e l'immagine `.png` in [`img/`](img/), con la stessa numerazione delle figure del
report. Lo schema ER (Figura 4) è in [er.md](er.md).

I nomi di classi, funzioni e file sono quelli del codice in `src/` e `tools/`.

| Figura | Cosa mostra | File in `img/` |
|---|---|---|
| 1 | Casi d'uso | `01_casi_uso` |
| 2a | Classi: harness (Runner, Chat, RunAgent) | `02a_classi_harness` |
| 2b | Classi: livello modello (client LLM) | `02b_classi_llm` |
| 2c | Classi: messaggi, risposte ed errori | `02c_classi_messaggi` |
| 2d | Classi: server MCP, back-end, database | `02d_classi_server` |
| 3a | Sequenza: il ciclo agentico (runAgent) | `03a_sequenza_ciclo` |
| 3b | Sequenza: esecuzione di un tool MCP e conferma umana | `03b_sequenza_tool` |
| 3c | Sequenza: variante con conferma negata | `03c_sequenza_conferma_negata` |
| 4 | Schema ER | [er.md](er.md) |

---

## Figura 1 — Diagramma dei casi d'uso

L'operatore SOC chiede un compito in linguaggio naturale. Il modello (attore
secondario) sceglie i tool; le due azioni che scrivono sul DB passano per la
conferma dell'operatore.

```mermaid
flowchart LR
    op(["Operatore SOC"])
    llm(["Modello LLM"])

    subgraph sys["Cyber-SOC Sentinel"]
        direction TB
        uc1("Chiedere un compito<br/>in linguaggio naturale")
        uc2("Leggere i log di rete")
        uc3("Verificare la reputazione<br/>di un IP")
        uc4("Isolare un IP")
        uc5("Aprire un ticket<br/>di incidente")
        uc6("Confermare o negare<br/>un'azione di scrittura")
        uc7("Consultare il log JSONL<br/>e il riassunto del run")
    end

    op --- uc1
    op --- uc6
    op --- uc7
    llm --- uc2
    llm --- uc3
    llm --- uc4
    llm --- uc5

    uc1 -.->|include| uc2
    uc4 -.->|include| uc6
    uc5 -.->|include| uc6
    uc3 -.->|extend| uc1
```

*Figura 1: sorgente [`img/01_casi_uso.mmd`](img/01_casi_uso.mmd), immagine [`img/01_casi_uso.png`](img/01_casi_uso.png).*

**Come si legge.** L'operatore avvia il compito (`uc1`) e può rispondere alle
conferme (`uc6`) e rileggere il log (`uc7`). Il modello usa i quattro tool. Isolare
un IP e aprire un ticket **includono sempre** la conferma: senza un sì esplicito non si
scrive nulla (fail closed).

---

## Figura 2 — Diagramma delle classi (server MCP + harness)

Tre blocchi: **harness** (`agent.py`, `mcp_client.py`, `run_agent.py`, `chat.py`, `tools/runner.py`),
**livello modello** (`llm/`, sostituibile senza toccare il resto) e **server MCP** con il
back-end. Il diagramma è diviso in quattro figure per restare leggibile.

### Figura 2a — Harness

```mermaid
classDiagram
    direction TB
    class Runner {
        <<tools/runner.py>>
        +eseguiScenario(scenario, ripetizione, client, outDir, seed) dict
        +valuta(result, controlli) dict
        +scriviRiepilogo(outDir)
        +scriviConfronto(outDirs, percorso)
    }
    class Scenario {
        +numero int
        +titolo str
        +richiesta str
        +atteso str
        +risposta str
        +controlli Callable
    }
    class Controllo {
        +nome str
        +ok bool
        +dettaglio str
    }
    class Chat {
        <<chat.py>>
        +rispondi(frase)
        +azzera()
        -_eventiDa(inizio) list
    }
    class RunAgentCLI {
        <<run_agent.py>>
        +buildClient(provider, env, model) LLMClient
        +makeAsk(answer) Callable
        +main(args) int
    }
    class Modelli {
        <<modelli.py>>
        +elencoModelli(env) list
        +costruisci(voce, env) LLMClient
    }
    class Interfaccia {
        <<interfaccia.py>>
        +mostraBanner()
        +creaInput(cronologia)
        +Attesa
    }
    class RunAgent {
        <<agent.py>>
        +runAgent(client, tools, callTool, userRequest, ...) AgentResult
        +formatSummary(result) str
        +logEvent(file, tipo, dati)
    }
    class AgentResult {
        +motivoArresto str
        +testoFinale str
        +giri int
        +tokenTotali int
        +toolRiusciti int
        +toolFalliti int
        +toolRifiutati int
    }
    class Trascrizione {
        <<trascrizione.py>>
        +righeSessione(richiesta, eventi, result) list
        +logLeggibile(eventi) str
    }
    class McpToolClient {
        +tools list
        +ask Callable
        +callTool(name, arguments) Any
    }
    class LLMClient {
        <<abstract>>
        +chat(messages, tools, temperature) LLMResponse
    }
    Runner o-- "12" Scenario
    Scenario ..> Controllo : controlli() produce
    Runner ..> Chat : stesso motore della chat
    Runner ..> Trascrizione : output.txt e screenshot
    Chat ..> RunAgent : un giro per messaggio
    Chat ..> McpToolClient : avviato una volta
    Chat ..> Trascrizione : mostra i passaggi
    Chat ..> Modelli : sceglie il modello
    Chat ..> Interfaccia : banner e input
    Modelli ..> RunAgentCLI : buildClient()
    Runner ..> RunAgentCLI : buildClient()
    RunAgentCLI ..> RunAgent : avvia
    RunAgentCLI ..> McpToolClient : crea
    RunAgent --> AgentResult : restituisce
    RunAgent ..> LLMClient : chat()
    RunAgent ..> McpToolClient : callTool()
```

*Figura 2a: sorgente [`img/02a_classi_harness.mmd`](img/02a_classi_harness.mmd), immagine [`img/02a_classi_harness.png`](img/02a_classi_harness.png).*

### Figura 2b — Livello modello

```mermaid
classDiagram
    direction TB
    class LLMClient {
        <<abstract>>
        +model str
        +chat(messages, tools, temperature) LLMResponse
    }
    class OpenAICompatibleClient {
        Gemini, Mistral, NVIDIA, Ollama
        5 tentativi su errori temporanei
        legge il tool scritto come testo
    }
    class FallbackClient {
        prova i modelli in ordine
        scatta solo su errori temporanei
    }
    class FakeLLMClient {
        risposte preparate, per i test
    }
    class Pensiero {
        <<pensiero.py>>
        +separaPensiero(testo)
    }
    LLMClient <|-- OpenAICompatibleClient
    LLMClient <|-- FallbackClient
    LLMClient <|-- FakeLLMClient
    FallbackClient o-- "2..n" LLMClient
    OpenAICompatibleClient ..> Pensiero : toglie i tag thought/think
```

*Figura 2b: sorgente [`img/02b_classi_llm.mmd`](img/02b_classi_llm.mmd), immagine [`img/02b_classi_llm.png`](img/02b_classi_llm.png).*

### Figura 2c — Messaggi, risposte ed errori

```mermaid
classDiagram
    direction TB
    class LLMResponse {
        +content str
        +toolCalls list
        +usage Usage
        +model str
        +finishReason str
        +latencySeconds float
        +thinking str
        +fallback str
        +toolDaTesto bool
    }
    class Usage {
        +promptTokens int
        +completionTokens int
        +totalTokens int
    }
    class ToolCall {
        +id str
        +name str
        +arguments dict
        +invalidArguments str
        +extraContent dict
    }
    class Message {
        +role str
        +content str
        +toolCalls list
        +toolCallId str
    }
    class LLMError {
        <<exception>>
        +statusCode int
    }
    class TransientLLMError {
        +retryAfterSeconds float
    }
    class PermanentLLMError
    LLMResponse *-- Usage
    LLMResponse o-- ToolCall
    Message o-- ToolCall
    LLMError <|-- TransientLLMError
    LLMError <|-- PermanentLLMError
```

*Figura 2c: sorgente [`img/02c_classi_messaggi.mmd`](img/02c_classi_messaggi.mmd), immagine [`img/02c_classi_messaggi.png`](img/02c_classi_messaggi.png).*

### Figura 2d — Server MCP, back-end e database

```mermaid
classDiagram
    direction LR
    class McpToolClient {
        +tools list
        +ask Callable
        +callTool(name, arguments) Any
        -_elicit(...) conferma Y/N
    }
    class McpServer {
        <<mcp_server.py>>
        +readLogs(ip, statusCode, limit) dict
        +checkReputation(ip) dict
        +isolateIp(ip, reason, ctx) dict
        +openTicket(title, description, severity, relatedIp, ctx) dict
        -askConfirmation(ctx, message) dict
    }
    class Backend {
        <<backend.py>>
        +readLogs()
        +checkReputation()
        +validateIsolation()
        +isolateIp()
        +validateTicket()
        +openTicket()
    }
    class Database {
        <<SQLite>>
        network_logs
        assets
        ip_whitelist
        threat_intel_db
        isolated_ips
        incident_tickets
    }
    McpToolClient ..> McpServer : MCP su stdio
    McpServer ..> Backend
    Backend ..> Database
```

*Figura 2d: sorgente [`img/02d_classi_server.mmd`](img/02d_classi_server.mmd), immagine [`img/02d_classi_server.png`](img/02d_classi_server.png).*

**Punti chiave per la discussione.**
- `RunAgent` conosce solo l'interfaccia `LLMClient`: Gemini, Mistral, NVIDIA, Ollama, il
  fallback e il finto per i test sono intercambiabili (Figura 2b).
- `callTool` è passata da fuori: in test è un finto, in produzione è
  `McpToolClient.callTool`.
- La conferma parte dal **server** (`askConfirmation`, elicitation MCP) e l'harness la
  inoltra al callback `ask`: a mano `input` (risposte S/Y o N), in automatico `yes`/`no`.
- `Runner` e `Chat` usano lo stesso motore (`RunAgent`): i test non provano una copia
  del codice, ma quello che si usa a mano.

---

## Figura 3 — Diagramma di sequenza

Il ciclo agentico è diviso in due diagrammi da cinque colonne ciascuno, più la variante
con conferma negata. Il primo mostra cosa fa l'harness, il secondo cosa succede dentro un
tool.

### Figura 3a — Il ciclo agentico (`runAgent`)

Avvio della sessione, ciclo con al massimo 10 iterazioni, chiamata al modello,
validazione dei parametri prima di eseguire e delega a `callTool`.

```mermaid
sequenceDiagram
    autonumber
    actor Op as Operatore SOC
    participant RA as run_agent.py
    participant H as runAgent (harness)
    participant LLM as LLMClient
    participant MCP as McpToolClient

    Op->>RA: --request "Analizza i log e isola gli IP ostili"
    RA->>MCP: avvia sessione stdio (initialize + list_tools)
    MCP-->>RA: 4 tool con schema dei parametri
    RA->>H: runAgent(client, tools, callTool, richiesta)
    Note over H: messages = [system, user]<br/>log JSONL: "richiesta"

    loop Fino a risposta finale o max 10 iterazioni
        H->>LLM: chat(messages, tools)
        LLM-->>H: LLMResponse (testo o toolCalls) + token
        Note over H: log "risposta" (modello, token)

        alt nessuna toolCall
            H-->>RA: AgentResult (risposta finale)
        else ci sono toolCalls
            H->>H: valida: tool esiste? JSON e schema validi?
            alt non valida
                Note over H: NON esegue, aggiunge errore a messages<br/>log esito "rifiutato"
            else valida
                H->>MCP: callTool(nome, argomenti) [vedi sequenza_tool]
                MCP-->>H: risultato del tool (o errore / timeout)
                Note over H: log "tool_chiamato" + "risultato"<br/>aggiunge messaggio tool a messages
            end
        end
    end

    RA->>Op: formatSummary(result) + risposta finale
```

*Figura 3a: sorgente [`img/03a_sequenza_ciclo.mmd`](img/03a_sequenza_ciclo.mmd), immagine [`img/03a_sequenza_ciclo.png`](img/03a_sequenza_ciclo.png).*

### Figura 3b — Esecuzione di un tool MCP e conferma umana

Cosa succede dentro `callTool`: il protocollo MCP con timeout di 30 s, il bivio tra tool di
lettura e di scrittura, la conferma S/N dell'operatore (dopo 3 risposte non valide vale come
rifiuto) e la scrittura sul DB solo se confermata.

```mermaid
sequenceDiagram
    autonumber
    actor Op as Operatore SOC
    participant H as runAgent (harness)
    participant MCP as McpToolClient
    participant Srv as Server MCP
    participant DB as Backend + DB

    H->>MCP: callTool(nome, argomenti)
    MCP->>Srv: call_tool (stdio, timeout 30 s)

    alt tool di sola lettura (readLogs / checkReputation)
        Srv->>DB: SELECT su network_logs / threat_intel_db / assets
        DB-->>Srv: record trovati
    else tool di scrittura (isolateIp / openTicket)
        Srv->>DB: validateIsolation / validateTicket
        Srv->>MCP: elicitation "Confermi?" (ctx.elicit)
        MCP->>Op: mostra la domanda [S/N] (callback ask)
        Op-->>MCP: S oppure N
        Note over MCP: log "conferma" (esito Y/N)<br/>dopo 3 risposte non valide = rifiuto
        MCP-->>Srv: ElicitResult (confirm = True / False)

        alt Operatore conferma (S)
            Srv->>DB: INSERT su isolated_ips / incident_tickets
            DB-->>Srv: conferma scrittura
        else Operatore rifiuta (N)
            Note over Srv: nessuna scrittura<br/>restituisce "cancelled"
        end
    end

    Srv-->>MCP: risultato JSON (o errore)
    MCP-->>H: risultato decodificato
```

*Figura 3b: sorgente [`img/03b_sequenza_tool.mmd`](img/03b_sequenza_tool.mmd), immagine [`img/03b_sequenza_tool.png`](img/03b_sequenza_tool.png).*

### Figura 3c — Variante: conferma negata

```mermaid
sequenceDiagram
    autonumber
    actor Op as Operatore SOC
    participant H as runAgent
    participant LLM as LLMClient
    participant MC as McpToolClient
    participant S as Server MCP

    H->>MC: callTool("isolateIp", {ip, reason})
    MC->>S: call_tool
    S-->>MC: elicitation "Confermi? Y/N"
    MC->>Op: domanda
    Op-->>MC: N
    MC-->>S: conferma = N
    Note over S: validazione già passata,<br/>nessuna scrittura sul DB
    S-->>MC: {cancelled: true, message: "..."}
    MC-->>H: risultato "cancelled" (esito N nel log)
    H->>LLM: chat(messages con il risultato)
    LLM-->>H: "Operazione annullata dall'operatore"
```

*Figura 3c: sorgente [`img/03c_sequenza_conferma_negata.mmd`](img/03c_sequenza_conferma_negata.mmd), immagine [`img/03c_sequenza_conferma_negata.png`](img/03c_sequenza_conferma_negata.png).*

---

## Figura 4 — Schema ER

Vedi [er.md](er.md): sei tabelle (`network_logs`, `assets`, `ip_whitelist`,
`threat_intel_db`, `isolated_ips`, `incident_tickets`).
