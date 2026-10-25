# Schema ER — Cyber-SOC Sentinel

Le 6 tabelle del DB SQLite (definizione in [schema.sql](../schema.sql)).

```mermaid
erDiagram
    NETWORK_LOGS {
        int id PK
        text timestamp
        text ip
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
        text ip_correlato
        int status_code_correlato
        text timestamp
        text stato
    }

    ASSETS ||--o| IP_WHITELIST : "ip (puo' essere in whitelist)"
    NETWORK_LOGS }o--o| ASSETS : "ip sorgente"
    NETWORK_LOGS }o--o| THREAT_INTEL_DB : "ip sorgente"
    NETWORK_LOGS }o--o| ISOLATED_IPS : "ip isolato dopo analisi"
    NETWORK_LOGS ||--o{ INCIDENT_TICKETS : "ip_correlato / status_code_correlato"
```

## Note

- **Nessuna chiave esterna:** le relazioni sono *logiche*, passano dal campo
  `ip`. `network_logs` contiene anche IP esterni che non compaiono in nessuna
  altra tabella, quindi un vincolo FK sarebbe sbagliato. Le tabelle di
  contesto (`assets`, `ip_whitelist`, `threat_intel_db`) si consultano con
  `verifica_reputazione`.
- **Tabelle di sola lettura per l'agente:** `network_logs`, `assets`,
  `ip_whitelist`, `threat_intel_db`.
- **Tabelle scritte dall'agente (con conferma Y/N):** `isolated_ips`
  (`isola_ip`) e `incident_tickets` (`apri_ticket`).
- **`user_agent`** e' dato non fidato (vedi scenario 7, prompt injection).
