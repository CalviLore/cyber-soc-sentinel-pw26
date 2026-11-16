# Dichiarazione sull'uso di assistenti AI

## Strumenti utilizzati
- **Claude Code (Anthropic):** assistente di programmazione e scrittura utilizzato in modalità collaborativa (*pair programming*) sotto la direzione tecnica dell'autore.
- **Modelli linguistici del prototipo (Gemini, Gemma, Mistral/Ministral, Nemotron, phi4-mini):** costituiscono il *prodotto* oggetto di sperimentazione, non gli strumenti impiegati per sviluppare il progetto.

## Contributo dell'autore
L'autore ha ideato, progettato, scritto, diretto e validato l'intero lavoro. In particolare:
- **Sviluppo del codice applicativo:** simulatore e schema del database, back-end, server MCP, client dei modelli e harness agentico;
- **Definizione del perimetro:** contestualizzazione su un SOC di primo livello, progettazione dei 4 tool e definizione dei 12 scenari di test;
- **Strategia sui modelli:** selezione delle coppie cloud/locale per produttore (Google, Mistral, NVIDIA), meccanismo di fallback (`Gemini → Gemma 4 31B`), dimensionamento fino a 8B sui modelli locali ed esclusione dei provider cinesi per motivi di governance dei dati;
- **Analisi e ricerca:** valutazione delle specifiche tecniche, dei piani gratuiti e dei listini, con relativa documentazione delle fonti;
- **Sperimentazione:** progettazione ed esecuzione dei 12 scenari sugli 8 modelli (4 cloud e 4 locali) e interpretazione critica dei risultati;
- **Impostazione editoriale e grafica:** definizione dei diagrammi UML, delle figure, delle tabelle e degli snippet (selezione degli elementi, livello di dettaglio) e revisione puntuale di ogni versione.

## Supporto dell'assistente
L'assistente ha operato esclusivamente su specifiche, vincoli e revisione continua dell'autore.

**Attività eseguite su specifiche e supervisione dell'autore:**
- Generazione assistita dei test unitari (194 test automatici superati), basata sui casi limite e sui requisiti definiti dall'autore, seguita da revisione ed esecuzione;
- Automazione dei controlli di coerenza incrociata tra i log di esecuzione, lo stato del database e le tabelle riportate nel report.

**Attività svolte in collaborazione con l'autore:**
- Confronto tecnico e valutazione critica sulle scelte architetturali e sulle soluzioni di implementazione;
- Redazione della documentazione tecnica (`docs/`, `TOOL_MCP.md`, `decision-log.md`, diario di sviluppo) e di script di servizio (es. `tools/elenca_modelli.py`);
- Generazione di diagrammi UML, figure, tabelle e snippet a partire dai file del repository, secondo le indicazioni progettuali e la validazione finale dell'autore;
- Brainstorming sulla struttura del report, revisione linguistica (ortografia, grammatica, punteggiatura) e proposte di sintesi testuale, tutte vagliate e approvate dall'autore.

## Ripartizione per modulo

| Modulo | Responsabilità e sviluppo | Modalità di verifica |
| :--- | :--- | :--- |
| Simulatore e database | Scritto dall'autore | Seed fisso, controlli sulle tabelle |
| Back-end (`backend.py`) | Scritto dall'autore | Test automatici |
| Server MCP (`mcp_server.py`) | Scritto dall'autore | Test end-to-end |
| Client dei modelli e harness | Scritto dall'autore | Esecuzione dei 12 scenari |
| Test unitari | Generati su specifiche dell'autore, revisionati dall'autore | Esecuzione suite di test |
| Documentazione | Redatta in collaborazione, revisionata e approvata dall'autore | Lettura critica e correzioni dell'autore |
