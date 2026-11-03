# Diario di sviluppo — Cyber-SOC Sentinel

Log cronologico: 2 righe per modulo chiuso.

## 2026-09-24
- Modulo: setup iniziale del repository.
- Note: Fase 0 avviata.

## 2026-10-21 → 2026-10-25
- Modulo: setup dell'ambiente.
- Note: installazione di strumenti, modelli e librerie, prime scelte di progetto.

## 2026-10-25
- Modulo: Fase 1 — schema.sql (6 tabelle), db.py, simulatore.py a comandi (/scenario, /clear), schema ER in docs/er.md.
- Note: dati deterministici (seed 42, T0 20/10/2026 10:00). Installati faker, mcp, jsonschema nel venv.
- Modifica: IP degli attaccanti (brute force, multitool, injection) generati dal seed invece che fissi nel codice; aggiunti comandi /ip e /seed N al simulatore. Motivo: valutare l'agente sul comportamento, non sull'indirizzo.
- Modifica: tutti gli IP (anche whitelist, threat intel, asset interni) generati dal seed; quantita' di log casuali in range configurabili (RANGE_*); nuovo scenario di controllo /login-sbagliato. Il simulatore crea solo fatti, le risposte attese stanno solo nei test.

## 2026-10-29
- Modulo: Fase 2 — back-end (src/backend.py) con le 4 funzioni readLogs, checkReputation, isolateIp, openTicket e 12 test in tests/test_backend.py.
- Note: la logica sui dati sta qui, il server MCP non ne ha. Codice in camelCase (tranne tabelle e colonne SQL). docs/backend.md e docs/er.md riscritti come specifica tecnica, con nomi di tool ed errori allineati al codice.
- Modulo: Fase 2 — server MCP (src/mcp_server.py) con i 4 tool, SDK mcp 2.x (MCPServer), trasporto stdio. 8 test end-to-end in tests/test_mcp_server.py.
- Note: isolateIp e openTicket validano, poi chiedono Y/N al server (ctx.elicit), poi scrivono; se la conferma non è disponibile rifiutano (fail closed).

## 2026-11-01
- Modulo: Fase 2 — fault injection lato server: con FAULT_TIMEOUT=1 checkReputation non risponde mai (scenario 8). 2 test aggiunti, 22 test totali.
- Note: TOOL_MCP.md aggiornato. Fase 2 chiusa.

## 2026-11-03
- Modulo: scelta dei modelli per l'harness (Fase 3, ancora nessun codice dell'harness). Famiglie Google (Gemini + Gemma) e Mistral in prova; scaricati ministral-3:8b e gemma4:e4b ufficiali Ollama e le versioni Unsloth UD-Q3_K_XL; chiavi e nomi dei modelli in .env.
- Note: le decisioni con i motivi sono in decision-log.md; stima dei token e spunti per il report in IDEE.md; vincoli e indice del testo in tesi/VINCOLI_TESTO.md.
