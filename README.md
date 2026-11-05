# Cyber-SOC Sentinel

Project Work — L-31 Informatica per le Aziende Digitali (UniPegaso), Traccia
PW26: integrazione di un AI agent nel sistema informativo di un'impresa —
server MCP (Model Context Protocol) + harness agentico.

## Setup

```bash
python -m venv venv

# Windows (PowerShell)
venv\Scripts\Activate.ps1
# macOS / Linux
source venv/bin/activate
```

```bash
pip install faker mcp jsonschema
```

## Struttura

```
src/        codice condiviso: db.py (connessione SQLite), schema.sql (6 tabelle)
tools/      simulatore.py — programma a parte che prepara i dati degli scenari
docs/       documentazione (schema ER)
data/       soc.db, generato dal simulatore (non versionato)
```

## Simulatore

```bash
python tools/simulatore.py            # modalita' interattiva, /help per i comandi
python tools/simulatore.py /clear /bruteforce /stato
```

`/clear` riporta il DB allo stato di base; `/bruteforce`, `/injection`,
`/multitool`... aggiungono la situazione di uno scenario. Gli IP e le
quantita' sono generati dal seed (`/seed N`, `/ip` per vederli).

## Harness agentico

```bash
python src/run_agent.py --provider gemini --request "Analizza i log e apri un ticket se serve"
python src/run_agent.py --provider mistral --answer yes   # conferma automatica
```

Il run stampa il riassunto preso da `AgentResult` e scrive il log JSONL in
`logs/agent-<data>.jsonl` (cartella ignorata da Git). I test:
`python -m unittest discover -s tests`.
