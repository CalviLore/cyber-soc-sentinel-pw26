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
| D012 | 2026-11-03 | Famiglie in prova: **Google** (Gemini + Gemma) e **Mistral** (API + Ministral); dal 6 novembre anche **NVIDIA** (vedi D025). Si sceglie dopo lo stesso test sui 4 tool | Tutte con piano gratuito e gemello locale; non scelgo a tavolino | In prova: tutte e tre entrano nei run finali |
| D013 | 2026-11-03 | Scartate: Qwen, IBM Granite, DeepSeek (e poi GLM e Kimi, vedi D026). NVIDIA era scartata, **riammessa il 6 novembre** (D025) | Qwen: su Groq è stessa famiglia ma non stesso produttore, piano Alibaba non verificato. IBM: circa 300.000 token al mese. DeepSeek: nessun piano gratuito ufficiale confermato, modelli piccoli orientati al ragionamento. NVIDIA: il 3 novembre il piano gratuito non era confermato, poi verificato | Presa (NVIDIA: rivista) |
| D014 | 2026-11-03 | Solo taglie grandi in locale: `ministral-3:8b` e `gemma4:e4b`. Eliminati `gemma4:e2b` e `ministral-3:3b` | Più capaci nel tool calling. Si accetta l'overflow su RAM e SSD (PC: 7,7 GB RAM, 4 GB VRAM) e quindi tempi lunghi | Presa |
| D015 | 2026-11-03 | Per ogni famiglia, versione ufficiale Ollama (Q4_K_M) e versione Unsloth `UD-Q3_K_XL` | Confronto facoltativo; scelta della Q3 al posto della Q4 per risparmiare memoria. Non isola un solo fattore (cambiano chi ha quantizzato e il livello) | **Abbandonata il 7 novembre**: già tagliata da D024, tolte le righe `UNSLOTH` da `.env` e `.env.example`; restano solo le versioni ufficiali Ollama |
| D016 | 2026-11-03 | La quantizzazione è un **limite dichiarato**, non un esperimento principale | Quantizzare riduce lo spazio ma anche la capacità; i risultati locali sono un limite inferiore | Presa |
| D017 | 2026-11-03 | Chiavi e modelli in `.env` (ignorato da Git), `.env.example` nel repository, `python-dotenv` nel venv | Nessuna chiave su GitHub; configurazione documentata | Presa |
| D018 | 2026-11-03 | Cambio di provider solo da `.env` (formato compatibile OpenAI) | Livello di astrazione richiesto dalla traccia | Presa (confermata il 2026-11-03: Gemini e Mistral rispondono con tool call dall'endpoint compatibile OpenAI) |
| D022 | 2026-11-03 | Cloud: il modello più forte che il piano gratuito permette davvero, non lo stesso peso del locale. Mistral: `mistral-large-4`. Google: `gemini-3.6-flash` (più `gemma-4-31b-it` disponibile in cloud) | Provati con una chiamata e un tool: Gemini Pro bloccato (429), `gemini-3.7-flash` e `3.8-flash` in errore 503 per domanda alta, `gemini-2.5-*` non più disponibili ai nuovi utenti; Mistral `medium-3.5`, `small-2603`, `magistral-medium` sempre 429. Limiti osservati su `mistral-large-4`: 20.000 token e 50 richieste al minuto, quindi il runner deve rallentare | Presa |
| D023 | 2026-11-03 | Cloud con **fallback**: si prova prima Gemini (`gemini-3.6-flash`), se non risponde (429, 5xx, timeout) si passa a Gemma 4 31B (`gemma-4-31b-it`), stessa chiave. Si parte dalla coppia Google; Mistral dopo | Gemini ha dato 503 per domanda alta e latenze di 65-75 secondi; il fallback evita che un run si fermi. Da fare: registrare nel log JSONL quale modello ha risposto, perché con un fallback i risultati di un run possono essere di modelli diversi | Presa |
| D024 | 2026-11-03 | Consegna finale anticipata al **20 novembre** (prima 29). Lavoro 3 giorni a settimana (giovedì, sabato, domenica): 7 giornate più il venerdì 20 per la verifica finale. Si tagliano le parti opzionali: baseline Fail2Ban, ripetizioni 3-5 → 2-3, confronto con le quantizzazioni Unsloth, run su tutti i modelli | Il piano precedente usava 12 giornate; il resto resta invariato. Paracadute 21-29 novembre | Presa |
| D025 | 2026-11-06 | **NVIDIA** entra come terza famiglia: cloud `nvidia/nemotron-3-ultra-550b-a55b` (NIM, endpoint compatibile OpenAI) e locale **Nemotron 3.5 Bolt E4B** (post-training NVIDIA di Gemma-4-E4B-it), stesso schema di D011 | Piano gratuito per prototipi (circa 40 richieste al minuto) verificato; il Ultra è il modello di punta della famiglia e passa i test sui tool. Per un'azienda reale i dati loggati su NIM sono un limite da dichiarare | Presa |
| D026 | 2026-11-06 | **Esclusi i modelli di origine cinese** (Qwen, DeepSeek, GLM, Kimi) anche se open o gratuiti | Mandare log di rete a un servizio in Cina non è credibile per un'azienda reale; coerente con lo scopo del progetto (SOC) | Presa |
| D027 | 2026-11-06 | **phi4-mini** (Microsoft) come modello piccolo di confronto in locale. Se scrive la chiamata al tool come testo, l'harness la riconosce (`toolDaTesto`, segnalato nel log) | Mostra cosa succede con un modello troppo piccolo; la tool call da testo è un adattamento dichiarato | Presa |
| D028 | 2026-11-05 | La chat (`src/chat.py`, classe `Chat` con memoria) e il runner (`tools/runner.py`, fuori da `src`) usano **lo stesso motore**; il runner non ha modelli finti: passa i dati a un LLM vero e controlla lo stato del DB e il log, non il testo | Un runner con risposte finte sembrerebbe predeterminato; il runner serve a noi per i giri automatici, non fa parte del prodotto | Presa |
| D029 | 2026-11-06 | Il **ragionamento è quello vero** del modello (Mistral `thinking`, Ollama `reasoning`, Gemini `include_thoughts`), non una richiesta nel prompt. Salvato nel log (`pensiero`), mai rimandato al modello | Mostrare come ragiona davvero il modello, senza barare; costa token e tempo, `PENSIERO=0` lo spegne | Presa |
| D030 | 2026-11-06 | Dati **uguali per tutti i modelli dentro un lancio, diversi tra un lancio e l'altro** (seed, IP, endpoint). Anche per il batch finale: un seed unico per tutti | Il confronto è sul ragionamento, non sugli indirizzi; lanci diversi non devono ripetere gli stessi dati | Presa |
| D031 | 2026-11-06 | Il **fallback** Gemini → Gemma si registra nel log con il motivo e nel `confronto.md` ("ha risposto X"); per i run veri si usa `--senza-riserva`. Gemini gratis: 20 richieste al giorno per modello | Con la quota finita il fallback falsava i risultati in silenzio | Presa |
| D032 | 2026-11-07 | **Prompt v2**: regola 4 (se l'operatore chiede un'azione e i fatti la giustificano, chiama il tool: la conferma la chiede il sistema), regola 8 (testo semplice, niente `**`), regola 9 (fuori ambito: due frasi, nessun tool). Richieste degli scenari 2, 3 e 5 con l'istruzione "isolalo". La v1 è salvata in `docs/PROMPT.md` | Con la v1 gli scenari 2 e 3 fallivano con tutti i modelli (chiedevano a parole "vuoi che isoli?"). Con la v2 passano su Mistral e Nemotron. Le run con la v1 sono di prova e non entrano nei confronti | Presa; da **congelare** prima delle run finali |
| D033 | 2026-11-07 | La conferma si mostra come **S/N**; si accetta anche Y. Nel log resta `Y`/`N` | Italiano per l'operatore; il log è il dato grezzo su cui contano i controlli | Presa |
| D034 | 2026-11-07 | Interfaccia della chat: banner, input con cronologia (`prompt_toolkit`), spinner e `/models` (`rich`), Markdown reso a video ma log e `output.txt` originali | Demo e screenshot leggibili; solo grafica, il server MCP non cambia | Presa |
| D035 | 2026-11-07 | Run finali con `LANCIA_TUTTO.ps1`: Mistral e NVIDIA 12 scenari × 2, Gemini solo scenari 2, 3 e 7, locali 12 × 1, un seed per tutti, prompt congelato prima | Una giornata di lavoro senza intervento (i locali sono lenti: 4 GB di VRAM) | Presa |

## Report e metodo

| ID | Data | Decisione | Motivo | Stato |
|---|---|---|---|---|
| D019 | 2026-11-03 | Nota di riproducibilità nel README (modelli e limiti dei piani gratuiti di novembre 2026) | Il progetto serve per il report; chi lo riprende deve sapere che le cose cambiano | Presa |
| D020 | 2026-11-03 | Il report unisce il meglio di due riferimenti (una tesi di esempio e `museo-hub`) in un testo proprio | Struttura da quelli, contenuto mio; vedi `tesi/VINCOLI_TESTO.md` | Presa |
| D021 | 2026-11-03 | Raccolta di spunti per report e orale in `IDEE.md` | Non perdere ragionamenti e fonti | Presa |

## Da decidere

| ID | Cosa | Cosa serve |
|---|---|---|
| P001 | Famiglia definitiva: Google, Mistral o NVIDIA | Confronto sui run finali (le tre famiglie sono già in prova, vedi D012 e D025) |
| P002 | Riprovare `gemini-3.7-flash` e `gemini-3.8-flash` (errore 503 per domanda alta) e capire il 429 di `mistral-medium-3.5`, `small-2603`, `magistral-medium` | Riprova in un altro momento; leggere i limiti nelle console |
| P003 | `limit` di default di `readLogs` (oggi 100, proposta 25) | Primo run con i token reali |
| P004 | Metodo di valutazione: tasso di successo per scenario con asserzioni sul DB | Conferma; è coerente con il passo 36 della scaletta |
| P005 | ~~Runner che salva ogni scenario e salta quelli già fatti~~ | Risolto: `tools/runner.py` con `--riprendi` (D028) |
| P006 | Fonte del limite di 6.000 parole | Controllare la roadmap del 24 settembre |
