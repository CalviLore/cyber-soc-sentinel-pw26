# Dichiarazione sull'uso di assistenti AI

## Strumenti utilizzati
- Claude Code (Anthropic), assistente di programmazione e di scrittura, usato durante il
  progetto.
- Modelli linguistici del prototipo (Gemini, Gemma, Mistral/Ministral, Nemotron, phi4-mini):
  sono il *prodotto* del progetto, non strumenti usati per costruirlo.

## Cosa ha fatto l'autore
L'autore ha ideato, scritto, diretto, eseguito e verificato il progetto. In particolare:
- il codice (simulatore e database, back-end, server MCP, client dei modelli e harness);
- la traccia e il perimetro (agente SOC di primo livello, 4 tool, 12 scenari);
- la scelta dei modelli: stesso produttore per cloud e locale, famiglie Google, Mistral e
  NVIDIA, fallback Gemini → Gemma 4 31B, taglie da 8B accettando i tempi lunghi, esclusione
  dei modelli di provider cinesi;
- le ricerche su modelli, piani gratuiti e riferimenti, con le fonti indicate;
- l'esecuzione dei 12 scenari con otto modelli (quattro cloud e quattro locali) e
  l'interpretazione dei risultati;
- l'impostazione dei diagrammi UML, delle figure, delle tabelle e degli snippet: cosa mostrare, con quali elementi e a quale livello di dettaglio, e la revisione di ogni versione.

## Supporto dell'assistente
L'assistente ha lavorato su specifiche e decisioni dell'autore.

Svolto dall'assistente:
- scrittura dei test unitari ed esecuzione e controllo dei test sugli scenari (194 test
  automatici passano).

Svolto insieme all'autore:
- consigli e valutazione delle idee dell'autore sulle scelte tecniche e sul lavoro di
  sviluppo;
- documentazione tecnica (`docs/`, `TOOL_MCP.md`, `decision-log.md`, diario di sviluppo) e
  script di servizio, per esempio `tools/elenca_modelli.py`;
- verifica dei dati riportati nel report rispetto a codice e log;
- diagrammi UML, figure, tabelle e immagini degli snippet, a partire dai file del
  repository e con le indicazioni e la revisione dell'autore;
- struttura del report (brainstorming), revisione ortografica, grammaticale e della
  punteggiatura, e proposte di riscrittura di parti del testo, poi riviste e approvate
  dall'autore.

## Ripartizione per modulo

| Modulo | Chi l'ha scritto | Come è stato verificato |
|---|---|---|
| Simulatore e database | scritto dall'autore | seed fisso, controlli sulle tabelle |
| Back-end (`backend.py`) | scritto dall'autore | test automatici |
| Server MCP (`mcp_server.py`) | scritto dall'autore | test end-to-end |
| Client dei modelli e harness | scritto dall'autore | scenari |
| Test unitari | scritti dall'assistente, riletti dall'autore | esecuzione dei 194 test |
| Documentazione | scritta insieme dall'autore e dall'assistente | lettura e correzioni dell'autore |
