# Diagrammi UML

Tre diagrammi richiesti dalla traccia (PW 26), in Mermaid: si vedono su GitHub e
nell'anteprima Markdown di VS Code (`Ctrl+Shift+V`). Lo schema ER è in [er.md](er.md).

I nomi di classi, funzioni e file sono quelli del codice in `src/`.

---

## 1. Diagramma dei casi d'uso

L'operatore SOC chiede un compito in linguaggio naturale. Il modello (attore
secondario) sceglie i tool; le due azioni che scrivono sul DB passano per la
conferma Y/N dell'operatore.

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

**Come si legge.** L'operatore avvia il compito (`uc1`) e può rispondere alle
conferme (`uc6`) e rileggere il log (`uc7`). Il modello usa i quattro tool. Isolare
un IP e aprire un ticket **includono sempre** la conferma: senza un "Y" non si
scrive nulla (fail closed).

---

## 2. Diagramma delle classi (server MCP + harness)

Tre blocchi: **harness** (`agent.py`, `mcp_client.py`, `run_agent.py`), **livello
modello** (`llm/`, sostituibile senza toccare il resto) e **server MCP** con il
back-end.

```mermaid
classDiagram
    direction TB

    %% ---------- Harness ----------
    class RunAgent {
        <<agent.py>>
        +runAgent(client, tools, callTool, userRequest, maxIterations, logFile, toolTimeoutSeconds) AgentResult
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
        +errore str
    }
    class McpToolClient {
        +tools list
        +ask Callable
        +callTool(name, arguments) Any
        -_elicit(...) conferma Y/N
    }
    class Chat {
        <<chat.py>>
        +history list
        +rispondi(richiesta) AgentResult
        +azzera()
        +eventi() list
    }
    class Runner {
        <<tools/runner.py>>
        +eseguiScenario(scenario, client, seed) dict
        +controlli DB e log
        +scriviRiepilogo() / scriviConfronto()
    }
    class Trascrizione {
        <<trascrizione.py>>
        +righeSessione(richiesta, eventi, result) list
        +logLeggibile(eventi) str
    }
    class RunAgentCLI {
        <<run_agent.py>>
        +buildClient(provider, env, model) LLMClient
        +makeAsk(answer) Callable
        +main(args) int
    }

    %% ---------- Livello modello ----------
    class LLMClient {
        <<abstract>>
        +model str
        +chat(messages, tools, temperature)* LLMResponse
    }
    class OpenAICompatibleClient {
        +chat(messages, tools, temperature) LLMResponse
    }
    class FallbackClient {
        +chat(messages, tools, temperature) LLMResponse
    }
    class FakeLLMClient {
        +moves list
        +calls list
        +chat(messages, tools, temperature) LLMResponse
    }
    class Message {
        +role str
        +content str
        +toolCalls list
        +toolCallId str
    }
    class ToolCall {
        +id str
        +name str
        +arguments dict
        +invalidArguments str
    }
    class LLMResponse {
        +content str
        +toolCalls list
        +usage Usage
        +model str
        +hasToolCalls bool
    }
    class Usage {
        +promptTokens int
        +completionTokens int
        +totalTokens int
    }
    class LLMError {
        <<exception>>
    }
    class TransientLLMError
    class PermanentLLMError

    %% ---------- Server MCP + back-end ----------
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
        +validateIsolation() / isolateIp()
        +validateTicket() / openTicket()
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

    %% ---------- Relazioni ----------
    Chat ..> RunAgent : un giro per messaggio
    Chat ..> McpToolClient : avviato una volta
    Chat o-- Message : memoria della conversazione
    Chat ..> Trascrizione : mostra i passaggi
    Runner ..> Chat : stesso motore della chat
    Runner ..> Trascrizione : output.txt e screenshot
    RunAgentCLI ..> RunAgent : avvia
    RunAgentCLI ..> McpToolClient : crea
    RunAgentCLI ..> LLMClient : buildClient
    RunAgent ..> LLMClient : chat()
    RunAgent ..> McpToolClient : callTool()
    RunAgent --> AgentResult : restituisce
    RunAgent o-- Message : memoria
    RunAgent ..> ToolCall : valida ed esegue

    LLMClient <|-- OpenAICompatibleClient
    LLMClient <|-- FallbackClient
    LLMClient <|-- FakeLLMClient
    FallbackClient o-- "2..n" LLMClient : prova in ordine
    LLMClient ..> LLMResponse
    LLMResponse *-- Usage
    LLMResponse o-- ToolCall
    Message o-- ToolCall
    LLMError <|-- TransientLLMError
    LLMError <|-- PermanentLLMError

    McpToolClient ..> McpServer : MCP su stdio
    McpServer ..> Backend
    Backend ..> Database
```

**Punti chiave per la discussione.**
- `RunAgent` conosce solo l'interfaccia `LLMClient`: Gemini, Mistral, Ollama, il
  fallback e il finto per i test sono intercambiabili.
- `callTool` è passata da fuori: in test è un finto, in produzione è
  `McpToolClient.callTool`.
- La conferma Y/N parte dal **server** (`askConfirmation`, elicitation MCP) e
  l'harness la inoltra al callback `ask`: a mano `input`, in automatico `yes`/`no`.

---

## 3. Diagramma di sequenza: un ciclo agentico completo

Scenario: l'operatore chiede di analizzare i log e, se serve, isolare un IP. Si
vedono due giri con tool di lettura, poi la scrittura con conferma, poi la risposta
finale. Sotto, la variante con conferma negata.

```mermaid
sequenceDiagram
    autonumber
    actor Op as Operatore SOC
    participant CLI as run_agent.py
    participant H as runAgent (harness)
    participant LLM as LLMClient
    participant MC as McpToolClient
    participant S as Server MCP
    participant B as Backend + DB

    Op->>CLI: --request "Analizza i log e isola gli IP ostili"
    CLI->>MC: avvia sessione (stdio)
    MC->>S: initialize + list_tools
    S-->>MC: 4 tool con schema dei parametri
    CLI->>H: runAgent(client, tools, callTool, richiesta)
    Note over H: messages = [system, user]<br/>log JSONL: "richiesta"

    loop fino a risposta finale o max iterazioni
        H->>LLM: chat(messages, tools)
        LLM-->>H: LLMResponse (testo oppure toolCalls) + token
        Note over H: log "risposta" (modello, token)

        alt nessuna toolCall
            H-->>CLI: AgentResult (risposta finale)
        else ci sono toolCalls
            H->>H: valida: tool esiste? argomenti validi? schema rispettato?
            alt non valida
                H->>H: NON esegue, messaggio tool di errore al modello
            else valida
                H->>MC: callTool(nome, argomenti)
                MC->>S: call_tool
                alt tool di lettura (readLogs / checkReputation)
                    S->>B: legge dal DB
                else tool di scrittura (isolateIp / openTicket)
                    S->>B: validateIsolation / validateTicket
                    S-->>MC: elicitation "Confermi? Y/N"
                    MC->>Op: mostra la domanda (callback ask)
                    Op-->>MC: Y
                    MC-->>S: conferma = Y
                    S->>B: scrive su isolated_ips / incident_tickets
                end

                B-->>S: risultato
                S-->>MC: risultato
                MC-->>H: risultato (o errore / timeout)
                Note over H: log "tool_chiamato" + "risultato"<br/>messaggio tool aggiunto a messages
            end
        end
    end

    CLI->>Op: formatSummary(result): motivo, giri, token, tool riusciti/falliti/rifiutati
```

### Variante: conferma negata

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
