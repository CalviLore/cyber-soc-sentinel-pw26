"""Chat a tastiera con l'harness: piu' richieste di fila, stessa memoria.

Il motore e' la classe Chat: apre il server MCP una volta sola e per ogni
frase dell'operatore chiama runAgent passandogli la storia della
conversazione. Cosi' il modello ricorda cosa ha gia' fatto (log letti, IP
isolati, ticket aperti) senza ripetere tutto a ogni domanda.

Uso:
    python src/chat.py --provider gemini
    python src/chat.py --provider mistral --db data/soc.db --answer yes

Nella chat:
    esci       chiude la sessione
    /nuova     azzera la memoria e ricomincia da capo
    (invio)    riga vuota, viene ignorata
    Ctrl+C     chiude la sessione (se il modello sta rispondendo, il run si
               ferma con motivo "interrotto")

Tutti gli eventi della sessione finiscono nello stesso log JSONL.
"""
import argparse
import asyncio
import json
import os
import shutil
import sys
import textwrap
from datetime import datetime
from pathlib import Path

from dotenv import dotenv_values

from agent import (
    MAX_ITERATIONS_DEFAULT,
    TOOL_TIMEOUT_SECONDS,
    logEvent,
    runAgent,
)
from llm.base import Message
from mcp_client import McpToolClient
from run_agent import buildClient, makeAsk
from interfaccia import Attesa, creaInput, mostraBanner, mostraHelp
from modelli import ansiColore, coloreModello, costruisci, elencoModelli, interpreta
from trascrizione import markdownInAnsi, righeSessione

ROOT = Path(__file__).resolve().parent.parent


# Colori ANSI per stile di riga (come lo screenshot del runner): il pensiero
# del modello e i risultati dei tool in grigio, i tool in azzurro, errori in rosso.
ANSI = {"pensiero": "90", "risultato": "90", "riepilogo": "90",
        "tool": "94", "errore": "91", "conferma": "93"}


def _stampa(righe, colori=True):
    """Stampa le righe della trascrizione a colori e a capo alla larghezza del
    terminale (senza spezzare le parole)."""
    larghezza = max(40, shutil.get_terminal_size((100, 30)).columns - 1)
    for stile, testo in righe:
        codice = ANSI.get(stile) if colori else None
        stato = (False, False)  # (grassetto, codice) di Markdown, a cavallo delle righe
        for originale in testo.split("\n"):
            rientro = len(originale) - len(originale.lstrip(" "))
            for pezzo in (textwrap.wrap(originale, larghezza,
                                        subsequent_indent=" " * rientro,
                                        drop_whitespace=True) or [""]):
                if colori:
                    pezzo, stato = markdownInAnsi(pezzo, stato)
                print(f"\033[{codice}m{pezzo}\033[0m" if codice else pezzo)


def _faultValue(fault) -> str:
    """Traduce il parametro fault nel valore di FAULT_TIMEOUT per il server.

    Accetta sia un booleano sia una stringa ("0"/"1", "on"/"off",
    "timeout"): in questo modo il valore puo' arrivare dal .env oppure dal
    codice senza casi speciali.
    """
    if fault is None:
        return "0"
    if isinstance(fault, bool):
        return "1" if fault else "0"

    value = str(fault).strip().lower()
    if value in ("", "0", "no", "off", "false", "none"):
        return "0"
    if value in ("1", "yes", "on", "true", "timeout"):
        return "1"
    return str(fault)


class Chat:
    """Motore della chat: un server MCP, una storia, molte richieste.

    client: LLMClient gia' costruito (es. con run_agent.buildClient).
    db: percorso SQLite; None usa il default del server (data/soc.db).
    fault: attiva la fault injection ("timeout"/True = FAULT_TIMEOUT=1).
    ask: callback di conferma Y/N per i tool di scrittura.
    logFile: log JSONL unico della sessione, condiviso con il server.
    maxIterations: tetto di giri per ogni singola richiesta.
    toolTimeout: timeout della singola chiamata a un tool.
    """

    def __init__(
        self,
        client,
        db: str | Path | None = None,
        fault=None,
        ask=input,
        logFile: str | Path | None = None,
        maxIterations: int = MAX_ITERATIONS_DEFAULT,
        toolTimeout: float | None = TOOL_TIMEOUT_SECONDS,
    ):
        self.client = client
        self.db = db
        self.fault = fault
        self.ask = ask
        self.logFile = logFile
        self.maxIterations = maxIterations
        self.toolTimeout = toolTimeout
        self.history: list[Message] = []
        self.eventi: list[dict] = []  # eventi dell'ultima richiesta, dal log
        self.mcp: McpToolClient | None = None

    async def __aenter__(self) -> "Chat":
        """Avvia il server MCP una volta sola e prepara i tool."""
        # Al server passano solo le variabili che gli servono: niente chiavi
        # API o altri segreti letti dal .env.
        mcpEnv = {"FAULT_TIMEOUT": _faultValue(self.fault)}
        if self.db:
            mcpEnv["SOC_DB"] = str(Path(self.db).resolve())

        self.mcp = McpToolClient(
            env=mcpEnv,
            logFile=self.logFile,
            ask=self.ask,
            toolTimeoutSeconds=self.toolTimeout,
        )
        await self.mcp.__aenter__()
        return self

    async def __aexit__(self, excType, exc, tb) -> None:
        """Chiude il server MCP; la storia resta disponibile per ispezioni."""
        if self.mcp is not None:
            await self.mcp.__aexit__(excType, exc, tb)
            self.mcp = None

    async def rispondi(self, frase: str):
        """Manda una frase al modello usando la storia e la aggiorna.

        Restituisce l'AgentResult del run: testo finale, motivo di arresto,
        conteggi e storia aggiornata.
        """
        if self.mcp is None:
            raise RuntimeError("Chat non avviata: usa 'async with'")

        inizioLog = self._dimensioneLog()
        result = await runAgent(
            self.client,
            self.mcp.tools,
            self.mcp.callTool,
            frase,
            history=self.history,
            maxIterations=self.maxIterations,
            logFile=self.logFile,
            toolTimeoutSeconds=self.toolTimeout,
        )
        # Il run restituisce la conversazione completa: e' la nuova memoria.
        self.history = result.history
        self.eventi = self._eventiDa(inizioLog)
        return result

    def _dimensioneLog(self) -> int:
        """Byte gia' scritti nel log: serve a leggere solo gli eventi nuovi."""
        if isinstance(self.logFile, (str, Path)) and Path(self.logFile).exists():
            return Path(self.logFile).stat().st_size
        return 0

    def _eventiDa(self, inizio: int) -> list[dict]:
        """Eventi del log scritti dopo `inizio` (quelli dell'ultima richiesta)."""
        if not isinstance(self.logFile, (str, Path)) or not Path(self.logFile).exists():
            return []
        with open(self.logFile, "rb") as f:
            f.seek(inizio)
            testo = f.read().decode("utf-8", errors="replace")
        return [json.loads(riga) for riga in testo.splitlines() if riga.strip()]

    def azzera(self) -> None:
        """Svuota la memoria: la prossima frase riparte dal system prompt."""
        self.history = []
        logEvent(self.logFile, "nuova_conversazione")


def parseArgs(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Chat interattiva con Cyber-SOC Sentinel"
    )
    parser.add_argument("--provider", choices=["gemini", "mistral", "nvidia", "ollama"],
                        default=None,
                        help="senza questo parametro la chat fa scegliere il modello "
                             "da un menu (in un terminale vero) oppure usa gemini")
    parser.add_argument("--model", help="sovrascrive il modello del .env")
    parser.add_argument("--db", help="percorso SQLite (default: data/soc.db)")
    parser.add_argument("--log", help="percorso del log JSONL della sessione")
    parser.add_argument("--max-iterations", type=int,
                        default=MAX_ITERATIONS_DEFAULT)
    parser.add_argument("--tool-timeout", type=float,
                        default=TOOL_TIMEOUT_SECONDS)
    parser.add_argument("--answer", choices=["ask", "yes", "no"],
                        default="ask",
                        help="conferma Y/N: interattiva oppure automatica")
    return parser.parse_args(argv)


def scegliVoce(env, corrente=None):
    """Mostra i modelli disponibili e fa scegliere un numero. None = nessuna scelta."""
    voci = elencoModelli(env)
    if not voci:
        print("Nessun modello disponibile: controlla le chiavi nel .env e che Ollama sia acceso.")
        return None
    print("\nModelli disponibili:")
    larghezza = max(len(v.etichetta) for v in voci)
    for i, v in enumerate(voci, 1):
        segno = "  (in uso)" if corrente and corrente == v.id else ""
        nome = ansiColore(f"{v.etichetta:<{larghezza}}", coloreModello(v.id))
        print(f"  {i:>2}. {nome}  {v.origine}{segno}")
    voce = interpreta(input("Numero (invio per annullare): "), voci)
    return voce


async def main(args: argparse.Namespace) -> int:
    env = dotenv_values(ROOT / ".env")
    if args.provider is None and not args.model and sys.stdin.isatty():
        voce = scegliVoce(env)
        if voce is None:
            return 0
        args.provider, args.model = voce.provider, voce.modello
    args.provider = args.provider or "gemini"
    client = buildClient(args.provider, env, args.model)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    logPath = (Path(args.log) if args.log
               else ROOT / "logs" / f"chat-{timestamp}.jsonl")
    logPath.parent.mkdir(parents=True, exist_ok=True)

    mostraBanner(client.model, args.provider, args.db or "data/soc.db", logPath)
    leggi = creaInput(ROOT / "logs" / ".cronologia")
    attesa = Attesa()

    logEvent(logPath, "sessione_inizio", provider=args.provider,
             modello=client.model)

    try:
        async with Chat(
            client,
            db=args.db,
            fault=env.get("FAULT_TIMEOUT", "0"),
            ask=attesa.conferma(makeAsk(args.answer)),
            logFile=logPath,
            maxIterations=args.max_iterations,
            toolTimeout=args.tool_timeout,
        ) as chat:
            while True:
                try:
                    frase = await leggi()
                except EOFError:
                    print("\n(uscita)")
                    break

                frase = frase.strip()
                if not frase:
                    continue

                comando = frase.lower()
                if comando in ("esci", "exit", "quit"):
                    break
                if comando == "/nuova":
                    chat.azzera()
                    print("(memoria azzerata: nuova conversazione)")
                    continue
                if comando in ("/help", "help", "?"):
                    mostraHelp()
                    continue
                if comando in ("/models", "/modelli", "/modello"):
                    voce = scegliVoce(env, chat.client.model)
                    if voce is None:
                        continue
                    try:
                        nuovo = costruisci(voce, env)
                    except ValueError as exc:
                        print(f"Non posso usare questo modello: {exc}")
                        continue
                    logEvent(logPath, "cambio_modello", da=chat.client.model,
                             a=nuovo.model)
                    chat.client = nuovo
                    print(f"(modello cambiato: ora {nuovo.model}; la conversazione "
                          f"continua. Con /nuova ricominci da capo.)")
                    continue

                attesa.avvia()
                try:
                    result = await chat.rispondi(frase)
                except Exception as exc:  # errore imprevisto, non del modello
                    attesa.ferma()
                    print(f"\nerrore imprevisto: {type(exc).__name__}: {exc}")
                    continue
                finally:
                    attesa.ferma()

                # Passaggi dell'agente, come in un terminale: tool chiamati con
                # i parametri, risultati, risposta. La domanda e la conferma
                # Y/N le hai gia' viste e scritte tu, quindi non si ripetono.
                print()
                _stampa(righeSessione(frase, chat.eventi, result,
                                      automatico=False,
                                      mostraRichiesta=False,
                                      mostraConferme=False,
                                      semplice=True))
                print()
                if result.errore:
                    # runAgent ha gia' fermato il run: la chat puo' continuare.
                    print("(la chat resta aperta: puoi riprovare)")
    except KeyboardInterrupt:
        print("\n(uscita)")
    finally:
        logEvent(logPath, "sessione_fine")

    return 0


if __name__ == "__main__":
    # Il modello puo' usare caratteri non presenti in cp1252.
    sys.stdout.reconfigure(encoding="utf-8")
    os.system("")  # abilita i colori ANSI nel terminale di Windows
    try:
        raise SystemExit(asyncio.run(main(parseArgs())))
    except KeyboardInterrupt:
        # Ctrl+C chiude la chat in modo pulito (il server MCP si ferma con
        # l'uscita da "async with"): per uscire senza interruzioni c'e' "esci".
        print("\n(uscita)")
        raise SystemExit(130)
