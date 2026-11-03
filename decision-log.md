# Decision log — Cyber-SOC Sentinel

Registro delle decisioni di progetto: una riga per decisione, con il motivo. Serve per
il capitolo sul processo di sviluppo e per rispondere alla domanda "perché hai scelto
questo?". Si aggiorna quando si decide qualcosa, non a fine lavoro.

Stato: **Presa** · **In prova** (deciso di provare, si conferma dopo un test) ·
**Proposta** (non ancora decisa) · **Superata** (sostituita da un'altra).

## Traccia, dati e back-end

| ID | Data | Decisione | Motivo | Stato |
|---|---|---|---|---|
| D001 | 2026-09-19 | Traccia PW 26: server MCP e harness agentico, impresa = SOC di primo livello ("Cyber-SOC Sentinel") | Il capitolato aggiornato sostituisce l'impresa culturale; il SOC dà tool di lettura e scrittura con rischio reale | Presa |
| D002 | 2026-10-25 | Base dati SQLite con 6 tabelle (`network_logs`, `assets`, `ip_whitelist`, `threat_intel_db`, `isolated_ips`, `incident_tickets`) | Relazionale come richiesto, senza server da installare | Presa |
| D003 | 2026-10-25 | Dati sintetici con Faker, seed 42, orologio fisso T0 = 20/10/2026 10:00 | Risultati ripetibili tra un'esecuzione e l'altra | Presa |
| D004 | 2026-10-25 | Il simulatore crea solo fatti; le risposte attese stanno solo nei test. IP generati dal seed, non fissi nel codice | Valutare l'agente sul comportamento, non sull'indirizzo | Presa |
| D005 | 2026-10-29 | Logica sui dati in `backend.py`; il server MCP chiama le funzioni senza logica propria | Back-end separato richiesto dalla traccia; codice testabile senza MCP | Presa |
| D006 | 2026-10-29 | Codice in camelCase, tranne nomi di tabelle e colonne SQL | Convenzione unica | Presa |
| D007 | 2026-10-29 | SDK ufficiale `mcp` 2.x (`MCPServer`), trasporto stdio | SDK ufficiale ammesso dalla traccia | Presa |
| D008 | 2026-10-29 | Tool di scrittura: prima validazione, poi conferma Y/N dal server (`ctx.elicit`), poi scrittura. Se la conferma non è disponibile, rifiuta (fail closed) | Nessuna scrittura senza conferma umana | Presa |
| D009 | 2026-11-01 | Fault injection lato server con `FAULT_TIMEOUT=1` | Provare lo scenario del tool in timeout | Presa |
| D010 | 2026-09 | Ciclo agentico scritto a mano, nessun framework agentico | Vincolo della traccia | Presa |

## Modelli linguistici (3 novembre 2026)

| ID | Data | Decisione | Motivo | Stato |
|---|---|---|---|---|
| D011 | 2026-11-03 | Cloud e locale dello **stesso produttore** | Cambia la taglia, non la famiglia: confronto pulito; schema realistico (cloud per i casi complessi, locale per i dati sensibili) | Presa |
| D012 | 2026-11-03 | Due famiglie in prova: **Google** (Gemini + Gemma) e **Mistral** (API + Ministral). Si sceglie dopo lo stesso test sui 4 tool | Entrambe nel piano gratuito, entrambe con gemello locale; non scelgo a tavolino | In prova |
| D013 | 2026-11-03 | Scartate: NVIDIA (Nemotron), Qwen, IBM Granite, DeepSeek | NVIDIA: piano gratuito non confermato, GGUF community. Qwen: su Groq è stessa famiglia ma non stesso produttore, piano Alibaba non verificato. IBM: circa 300.000 token al mese. DeepSeek: nessun piano gratuito ufficiale confermato, modelli piccoli orientati al ragionamento | Presa |
| D014 | 2026-11-03 | Solo taglie grandi in locale: `ministral-3:8b` e `gemma4:e4b`. Eliminati `gemma4:e2b` e `ministral-3:3b` | Più capaci nel tool calling. Si accetta l'overflow su RAM e SSD (PC: 7,7 GB RAM, 4 GB VRAM) e quindi tempi lunghi | Presa |
| D015 | 2026-11-03 | Per ogni famiglia, versione ufficiale Ollama (Q4_K_M) e versione Unsloth `UD-Q3_K_XL` | Confronto facoltativo; scelta della Q3 al posto della Q4 per risparmiare memoria. Non isola un solo fattore (cambiano chi ha quantizzato e il livello) | In prova |
| D016 | 2026-11-03 | La quantizzazione è un **limite dichiarato**, non un esperimento principale | Quantizzare riduce lo spazio ma anche la capacità; i risultati locali sono un limite inferiore | Presa |
| D017 | 2026-11-03 | Chiavi e modelli in `.env` (ignorato da Git), `.env.example` nel repository, `python-dotenv` nel venv | Nessuna chiave su GitHub; configurazione documentata | Presa |
| D018 | 2026-11-03 | Cambio di provider solo da `.env` (formato compatibile OpenAI) | Livello di astrazione richiesto dalla traccia | Presa (confermata il 2026-11-03: Gemini e Mistral rispondono con tool call dall'endpoint compatibile OpenAI) |
| D022 | 2026-11-03 | Cloud: il modello più forte che il piano gratuito permette davvero, non lo stesso peso del locale. Mistral: `mistral-large-4`. Google: `gemini-3.6-flash` (più `gemma-4-31b-it` disponibile in cloud) | Provati con una chiamata e un tool: Gemini Pro bloccato (429), `gemini-3.7-flash` e `3.8-flash` in errore 503 per domanda alta, `gemini-2.5-*` non più disponibili ai nuovi utenti; Mistral `medium-3.5`, `small-2603`, `magistral-medium` sempre 429. Limiti osservati su `mistral-large-4`: 20.000 token e 50 richieste al minuto, quindi il runner deve rallentare | Presa |
| D023 | 2026-11-03 | Cloud con **fallback**: si prova prima Gemini (`gemini-3.6-flash`), se non risponde (429, 5xx, timeout) si passa a Gemma 4 31B (`gemma-4-31b-it`), stessa chiave. Si parte dalla coppia Google; Mistral dopo | Gemini ha dato 503 per domanda alta e latenze di 65-75 secondi; il fallback evita che un run si fermi. Da fare: registrare nel log JSONL quale modello ha risposto, perché con un fallback i risultati di un run possono essere di modelli diversi | Presa |
| D024 | 2026-11-03 | Consegna finale anticipata al **20 novembre** (prima 29). Lavoro 3 giorni a settimana (giovedì, sabato, domenica): 7 giornate più il venerdì 20 per la verifica finale. Si tagliano le parti opzionali: baseline Fail2Ban, ripetizioni 3-5 → 2-3, confronto con le quantizzazioni Unsloth, run su tutti i modelli | Il piano precedente usava 12 giornate; il resto resta invariato. Paracadute 21-29 novembre | Presa |

## Report e metodo

| ID | Data | Decisione | Motivo | Stato |
|---|---|---|---|---|
| D019 | 2026-11-03 | Nota di riproducibilità nel README (modelli e limiti dei piani gratuiti di novembre 2026) | Il progetto serve per il report; chi lo riprende deve sapere che le cose cambiano | Presa |
| D020 | 2026-11-03 | Il report unisce il meglio di due riferimenti (una tesi di esempio e `museo-hub`) in un testo proprio | Struttura da quelli, contenuto mio; vedi `tesi/VINCOLI_TESTO.md` | Presa |
| D021 | 2026-11-03 | Raccolta di spunti per report e orale in `IDEE.md` | Non perdere ragionamenti e fonti | Presa |

## Da decidere

| ID | Cosa | Cosa serve |
|---|---|---|
| P001 | Famiglia definitiva: Google o Mistral | Test sui 4 tool su entrambe, limiti dei piani gratuiti letti nelle console |
| P002 | Riprovare `gemini-3.7-flash` e `gemini-3.8-flash` (errore 503 per domanda alta) e capire il 429 di `mistral-medium-3.5`, `small-2603`, `magistral-medium` | Riprova in un altro momento; leggere i limiti nelle console |
| P003 | `limit` di default di `readLogs` (oggi 100, proposta 25) | Primo run con i token reali |
| P004 | Metodo di valutazione: tasso di successo per scenario con asserzioni sul DB | Conferma; è coerente con il passo 36 della scaletta |
| P005 | Runner che salva ogni scenario appena finito e salta quelli già fatti | Decidere quando si scrive il runner (Fase 4) |
| P006 | Fonte del limite di 6.000 parole | Controllare la roadmap del 24 settembre |
