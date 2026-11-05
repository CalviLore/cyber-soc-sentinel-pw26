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

## 2026-11-05
- Modulo: Fase 3 — client LLM in src/llm/: LLMClient astratto (base.py), OpenAICompatibleClient (3 tentativi con attesa crescente, Retry-After rispettato), FakeLLMClient, FallbackClient. 53 test in tests/test_llm_*.py.
- Note: scelte di progetto: argomenti JSON rotti del modello non sollevano errore ma finiscono in ToolCall.invalidArguments (deciderà il ciclo agentico); i tool MCP si convertono nel formato OpenAI dentro il client; il fallback scatta solo su TransientLLMError. Rimosso il remote vecchio-origin.
- Prova dal vivo dei tre provider (Ollama ministral-3:8b, Gemini, Mistral) con una richiesta e un tool: tutti hanno chiamato readLogs con argomenti validi. La prova ha mostrato due problemi che i test finti non vedevano: Mistral con temperature=0 rifiuta la richiesta (errore 400) se top_p non è 1, e restituisce il contenuto come lista di blocchi (thinking + text) invece che come stringa. Corretti in OpenAICompatibleClient (top_p=1 a temperatura 0, _textOf tiene solo il testo), con 4 test nuovi (57 totali). Provati anche i modelli locali: ministral-3:8b, gemma4:e4b e Gemma Unsloth Q3 funzionano; Ministral Unsloth Q3 non parte (CUDA out of memory sulla RTX 3050 da 4 GB) ed è stato rimosso da Ollama. I test unitari li ha scritti Claude (da annotare in dichiarazione_AI.md).
