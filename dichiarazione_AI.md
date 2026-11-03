# Dichiarazione sull'uso di assistenti AI

Bozza del 3 novembre 2026. Le parti segnate *[da compilare]* sono quelle che solo
l'autore può dichiarare; non vanno riempite con ipotesi.

## Strumenti utilizzati
- Claude Code (Anthropic), assistente di programmazione e di scrittura, usato per tutto
  il progetto. Modello indicato nei commit: Claude Sonnet 5.5.
- Modelli linguistici del prototipo (Gemini, Gemma, Mistral/Ministral): sono il
  *prodotto* del progetto, non strumenti usati per costruirlo.

## Perché ho usato l'AI
Studio lavorando, quindi il tempo per il progetto è limitato (tre giorni a settimana, dopo
la sessione d'esami). L'assistente mi ha permesso di concentrarmi sulle decisioni di
progetto e sulla verifica dei risultati, che sono la parte che non si può delegare, e di
ridurre il tempo speso nella scrittura del codice e dei documenti. Il progetto riguarda
proprio l'integrazione di agenti AI in un'azienda: lavorare con un assistente è parte del
modo in cui questo tipo di sistemi si sviluppa oggi. *[adattare con parole proprie]*

## Cosa è stato fatto con l'AI
L'assistente ha **generato, controllato e ottimizzato** codice e documenti su specifiche
e decisioni dell'autore. In particolare:
- scrittura e revisione del codice e dei test *[da compilare: quali moduli, vedi tabella]*;
- documentazione tecnica (`docs/`, `TOOL_MCP.md`, `decision-log.md`, diario di sviluppo);
- script di servizio, per esempio `tools/elenca_modelli.py`;
- ricerche su modelli, piani gratuiti e riferimenti, con le fonti indicate;
- **gestione di Git**: commit e push su `origin`; i messaggi dei commit riportano la
  riga `Co-Authored-By`.

## Cosa è stato deciso e verificato dall'autore
L'autore ha **diretto, eseguito e verificato**. Le decisioni sono registrate con data e
motivo nel `decision-log.md`. Tra le principali:
- traccia e perimetro del progetto (agente SOC di primo livello, 4 tool, 12 scenari);
- scelta dei modelli: stesso produttore per cloud e locale, famiglie Google e Mistral in
  prova, fallback Gemini → Gemma 4 31B, taglie da 8B accettando i tempi lunghi;
- calendario e tagli (consegna il 20 novembre);
- cosa dichiarare e cosa no, e le correzioni di rotta su quanto proposto dall'assistente.

Verifiche eseguite: 22 test automatici passano (12 del back-end, 10 del server MCP);
chiamate di prova ai modelli cloud con un tool, con esito letto e interpretato
dall'autore.

## Cosa è stato scritto autonomamente
*[da compilare dall'autore: solo ciò che ha scritto o ideato da sé, anche se poco]*

## Ripartizione per modulo
*[da compilare dall'autore. Per ogni riga: "scritto da me", "scritto dall'AI e riletto da
me", oppure "scritto dall'AI".]*

| Modulo | Chi l'ha scritto | Come è stato verificato |
|---|---|---|
| Simulatore e database | *[da compilare]* | seed fisso, controlli sulle tabelle |
| Back-end (`backend.py`) | *[da compilare]* | 12 test |
| Server MCP (`mcp_server.py`) | *[da compilare]* | 10 test end-to-end |
| Client dei modelli e harness | *[da scrivere]* | scenari |
| Documentazione | AI, su indicazioni dell'autore | lettura e correzioni dell'autore |
| Report | scritto dall'autore | rilettura dell'autore |

## Riflessione critica
*[da compilare a fine progetto: cosa ha funzionato, cosa no, errori dell'assistente
corretti dall'autore, rischi dell'uso dell'AI in un progetto di questo tipo]*
