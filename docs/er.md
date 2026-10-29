# Schema ER — Cyber-SOC Sentinel

Le 6 tabelle del DB SQLite, definite in [../src/schema.sql](../src/schema.sql).
Il diagramma si vede renderizzato su GitHub e nell'anteprima Markdown di VS Code
(`Ctrl+Shift+V`).

```mermaid
erDiagram
    NETWORK_LOGS {
        int id PK
        text timestamp "ISO 8601"
        text ip "IPv4 sorgente"
        int status_code
        text method
        text endpoint
        text user_agent "dato NON fidato"
    }
    ASSETS {
        int id PK
        text ip UK
        text nome
        text tipo
        int critico "1 = mai da isolare"
    }
    IP_WHITELIST {
        int id PK
        text ip UK
        text motivo
    }
    THREAT_INTEL_DB {
        int id PK
        text ip UK
        int score "0-100"
        text motivo
    }
    ISOLATED_IPS {
        int id PK
        text ip UK
        text motivo
        text timestamp
        text operatore
    }
    INCIDENT_TICKETS {
        int id PK
        text titolo
        text descrizione
        text gravita "Bassa, Media, Alta"
        text ip_correlato "opzionale"
        int status_code_correlato "opzionale"
        text timestamp
        text stato "default: aperto"
    }

    NETWORK_LOGS }o--o| ASSETS : "ip = ip"
    NETWORK_LOGS }o--o| THREAT_INTEL_DB : "ip = ip"
    ASSETS |o--o| IP_WHITELIST : "ip = ip"
    NETWORK_LOGS }o--o| ISOLATED_IPS : "ip = ip"
    NETWORK_LOGS }o--o{ INCIDENT_TICKETS : "ip = ip_correlato"
```

## Come si legge

- Ogni riquadro è una tabella; `PK` = chiave primaria, `UK` = valore unico.
- Le linee uniscono tabelle che condividono lo stesso **indirizzo IP**.
  `}o--o|` significa "molti (anche zero) da un lato, al massimo uno dall'altro":
  per esempio molti log possono avere lo stesso IP, ma un IP compare al massimo
  una volta in `ISOLATED_IPS`. `|o--o|` è "al massimo uno da entrambi i lati" e
  `}o--o{` è "molti da entrambi i lati" (un IP può avere più ticket, un ticket
  può non riferirsi a nessun IP).

## Chi legge e chi scrive (tool MCP)

| Tabella | Tool | Accesso |
|---|---|---|
| `network_logs` | `leggi_log` | lettura |
| `assets`, `ip_whitelist`, `threat_intel_db` | `verifica_reputazione` | lettura |
| `isolated_ips` | `isola_ip` | **scrittura** (con conferma Y/N) |
| `incident_tickets` | `apri_ticket` | **scrittura** (con conferma Y/N) |

## Note

- **Nessuna chiave esterna:** le relazioni sono *logiche* e passano dal campo
  `ip`. `network_logs` contiene anche IP esterni che non compaiono in nessuna
  altra tabella: un vincolo FK li rifiuterebbe.
- **`user_agent`** è dato non fidato (scenario 7, prompt injection): l'agente
  lo tratta sempre come dato, mai come istruzione.
- **Dati generati dal seed:** gli IP e le quantità dei log cambiano con
  `/seed N` nel simulatore; lo schema resta lo stesso.
