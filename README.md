# Cyber-SOC Sentinel

Project Work — L-31 Informatica per le Aziende Digitali (UniPegaso), Traccia
PW26: integrazione di un AI agent nel sistema informativo di un'impresa —
server MCP (Model Context Protocol) + harness agentico scritto a mano, per un
SOC (Security Operations Center).

Il server MCP espone quattro tool su un database SQLite: `readLogs`,
`checkReputation` (sola lettura) e `isolateIp`, `openTicket` (scrittura, con
conferma dell'operatore S/N; senza conferma l'azione non parte). L'harness
(`runAgent`) fa girare il ciclo modello → tool → modello, con un tetto di 10
giri, e salva tutto in un log JSONL.

## Setup

```bash
python -m venv venv

# Windows (PowerShell)
venv\Scripts\Activate.ps1
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

Chiavi e modelli stanno nel file `.env` (mai su Git): si parte da
`.env.example`, che spiega ogni voce. Servono le chiavi dei provider cloud che
si vogliono usare (Google, Mistral, NVIDIA). I modelli locali girano con
[Ollama](https://ollama.com) e non hanno chiavi.

## Struttura

```
src/        server MCP e harness
  mcp_server.py   i 4 tool MCP        agent.py      ciclo agentico e prompt
  mcp_client.py   client e conferme   llm/          client LLM (OpenAI-compatibile)
  chat.py         chat a tastiera     interfaccia.py banner, input, spinner
  modelli.py      elenco e scelta dei modelli
  trascrizione.py resa a video e screenshot dei log
  db.py, schema.sql, backend.py       database SQLite (6 tabelle)
tools/      programmi di contorno, non fanno parte del prodotto
  simulatore.py   prepara i dati degli scenari
  runner.py       esegue i 12 scenari con un modello vero
  prova_tool.py, elenca_modelli.py
docs/       schema ER, diagrammi UML (Mermaid + PNG in docs/img), PROMPT.md
tests/      test automatici
data/       soc.db, generato dal simulatore (non versionato)
risultati/  output delle run (non versionato)
```

## Simulatore

```bash
python tools/simulatore.py            # modalita' interattiva, /help per i comandi
python tools/simulatore.py /clear /bruteforce /stato
```

`/clear` riporta il DB allo stato di base; `/bruteforce`, `/injection`,
`/multitool`... aggiungono la situazione di uno scenario. Gli IP e le
quantita' sono generati dal seed (`/seed N`, `/ip` per vederli).

## Chat

```bash
python src/chat.py                          # menu per scegliere il modello
python src/chat.py --provider mistral
python src/chat.py --provider ollama --model phi4-mini:latest
```

Dentro la chat: `/models` cambia modello senza perdere la conversazione,
`/nuova` azzera la memoria, `/help` elenca i comandi, `esci` chiude. Le azioni
di scrittura chiedono conferma: `S` (procedi) o `N` (annulla).

## Una richiesta sola

```bash
python src/run_agent.py --provider gemini --request "Analizza i log e apri un ticket se serve"
python src/run_agent.py --provider mistral --answer yes   # conferma automatica
```

Scrive il riassunto e il log JSONL in `logs/agent-<data>.jsonl` (ignorata da Git).

## Runner degli scenari

```bash
python tools/runner.py                          # menu: online/offline, modelli, scenari
python tools/runner.py --provider mistral --scenari 2 3 7 --ripetizioni 2
```

Per ogni run salva in `risultati/<data>-<modello>/scenario_NN/run_N/`:
`screenshot.png`, `output.txt`, `log_leggibile.txt`, `log.jsonl`,
`metriche.json`. Il runner controlla lo stato del database e il log, non il
testo della risposta. Con `--seed` si riproduce lo stesso caso; `--riprendi`
continua un lancio interrotto.

## Test

```bash
python -m unittest discover -s tests
```
