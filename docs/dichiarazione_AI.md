# Dichiarazione sull'uso di assistenti AI

## Strumenti utilizzati
- Claude Code (Anthropic): assistente di programmazione e di scrittura, usato quando serviva
  e sotto la direzione tecnica dell'autore.
- Modelli linguistici del prototipo (Gemini, Gemma, Mistral/Ministral, Nemotron, phi4-mini):
  costituiscono il prodotto oggetto di sperimentazione, non gli strumenti impiegati per
  sviluppare il progetto.

## Contributo dell'autore
L'autore ha ideato, progettato, scritto, diretto e validato il lavoro. In particolare:
- **Sviluppo del codice applicativo**: simulatore e schema del database, back-end, server MCP,
  client dei modelli e harness agentico;
- **Definizione del perimetro**: contestualizzazione su un SOC di primo livello, progettazione
  dei 4 tool e definizione dei 12 scenari di test;
- **Strategia sui modelli**: selezione delle coppie cloud/locale per produttore (Google,
  Mistral, NVIDIA), meccanismo di fallback (Gemini → Gemma 4 31B), dimensionamento fino a 8B
  sui modelli locali ed esclusione dei provider cinesi per motivi di governance dei dati;
- **Analisi e ricerca**: valutazione delle specifiche tecniche, dei piani gratuiti e dei
  listini, con relativa documentazione delle fonti;
- **Sperimentazione**: progettazione ed esecuzione dei 12 scenari sugli 8 modelli (4 cloud e
  4 locali) e interpretazione critica dei risultati;
- **Impostazione editoriale e grafica**: definizione dei diagrammi UML, delle figure, delle
  tabelle e degli snippet (selezione degli elementi, livello di dettaglio) e revisione
  puntuale di ogni versione.

## Supporto dell'assistente
L'assistente ha operato su specifiche, vincoli e revisione dell'autore.

Attività svolte in collaborazione con l'autore:
- confronto tecnico e valutazione critica sulle scelte architetturali e sulle soluzioni di
  implementazione;
- scrittura dei test unitari, svolta insieme all'autore e da lui revisionata ed eseguita;
- redazione della documentazione tecnica (docs/, TOOL_MCP.md) e di script di servizio (es.
  tools/elenca_modelli.py);
- decision-log.md e diario di sviluppo: le decisioni e i contenuti sono dell'autore, la
  stesura materiale è dell'assistente, su indicazione dell'autore;
- verifica dei dati riportati nel report rispetto a codice, log di esecuzione e stato del
  database;
- generazione di diagrammi UML, figure, tabelle e snippet a partire dai file del repository,
  secondo le indicazioni progettuali e la validazione finale dell'autore;
- brainstorming sulla struttura del report, revisione linguistica (ortografia, grammatica,
  punteggiatura) e proposte di sintesi testuale, tutte vagliate e approvate dall'autore.

## Ripartizione per modulo

| Modulo | Responsabilità e sviluppo | Modalità di verifica |
|---|---|---|
| Simulatore e database | Scritto dall'autore | Seed fisso, controlli sulle tabelle |
| Back-end (`backend.py`) | Scritto dall'autore | Test automatici |
| Server MCP (`mcp_server.py`) | Scritto dall'autore | Test end-to-end |
| Client dei modelli e harness | Scritto dall'autore | Esecuzione dei 12 scenari |
| Test unitari | Scritti insieme dall'autore e dall'assistente, revisionati dall'autore | Esecuzione suite di test |
| Documentazione | Contenuti dell'autore, stesura in collaborazione con l'assistente, revisionata e approvata dall'autore | Lettura critica e correzioni dell'autore |
