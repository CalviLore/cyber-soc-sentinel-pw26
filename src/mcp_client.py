"""Client MCP stdio: avvia mcp_server.py e offre un callTool vero all'harness.

Il ciclo agentico (agent.py) non conosce MCP: riceve solo una funzione
callTool(name, arguments). Questo modulo la costruisce parlando col server.

La conferma Y/N dei tool di scrittura arriva dal server come richiesta di
elicitation. Il client la mostra all'operatore, legge la risposta e la
restituisce al server; l'esito viene scritto nel log JSONL.

Uso tipico:
    async with McpToolClient(logFile="logs/run.jsonl") as mcp:
        risultato = await runAgent(client, mcp.tools, mcp.callTool, richiesta)
"""
import asyncio
import json
import os
import sys
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any, Callable

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import ElicitRequestParams, ElicitResult

from agent import TOOL_TIMEOUT_SECONDS, logEvent

SRC = Path(__file__).resolve().parent
DEFAULT_SERVER = SRC / "mcp_server.py"

# Se l'operatore scrive qualcosa che non e' Y/N, riprova un paio di volte;
# poi rinuncia (fail closed: nessuna scrittura senza un "si" esplicito).
MAX_CONFIRM_ATTEMPTS = 3

YES = {"y", "yes", "s", "si", "sì"}
NO = {"n", "no"}


def _parseAnswer(raw: str) -> bool | None:
    """True = Y, False = N, None = risposta non riconosciuta."""
    value = raw.strip().lower()
    if value in YES:
        return True
    if value in NO:
        return False
    return None


class McpToolClient:
    """Apre una sessione MCP stdio e espone tools + callTool.

    serverScript: percorso di mcp_server.py (default: quello accanto a questo file).
    env: variabili d'ambiente extra, es. {"SOC_DB": "...", "FAULT_TIMEOUT": "1"}.
    logFile: percorso del log JSONL, condiviso con agent.runAgent.
    ask: funzione che pone la domanda all'operatore (default input()).
    toolTimeoutSeconds: timeout della singola chiamata; None lo disabilita.
    """

    def __init__(
        self,
        serverScript: str | Path | None = None,
        env: dict[str, str] | None = None,
        logFile: str | Path | None = None,
        ask: Callable[[str], str] = input,
        toolTimeoutSeconds: float | None = TOOL_TIMEOUT_SECONDS,
    ):
        self.serverScript = Path(serverScript) if serverScript else DEFAULT_SERVER
        self.env = env or {}
        self.logFile = logFile
        self.ask = ask
        self.toolTimeoutSeconds = toolTimeoutSeconds
        self.tools: list[dict] = []
        self._session: ClientSession | None = None
        self._stack: AsyncExitStack | None = None

    async def __aenter__(self) -> "McpToolClient":
        """Avvia il processo del server, inizializza la sessione e legge i tool."""
        params = StdioServerParameters(
            command=sys.executable,
            args=[str(self.serverScript)],
            env={**os.environ, **self.env},
        )
        stack = AsyncExitStack()
        try:
            read, write = await stack.enter_async_context(stdio_client(params))
            self._session = await stack.enter_async_context(
                ClientSession(
                    read,
                    write,
                    elicitation_callback=self._elicit,
                )
            )
            await self._session.initialize()
            result = await self._session.list_tools()
        except BaseException:
            await stack.aclose()
            raise

        self._stack = stack
        # Formato MCP con inputSchema: e' quello che si aspetta LLMClient.chat,
        # che poi lo traduce nel formato OpenAI.
        self.tools = [
            {
                "name": tool.name,
                "description": tool.description or "",
                # L'SDK 2.x espone input_schema (snake_case); il resto del
                # progetto usa inputSchema, che e' il nome nel protocollo MCP
                # e quello atteso da OpenAICompatibleClient._toSdkTools.
                "inputSchema": (
                    getattr(tool, "inputSchema", None)
                    or getattr(tool, "input_schema", None)
                    or {}
                ),
            }
            for tool in result.tools
        ]
        return self

    async def __aexit__(self, excType, exc, tb) -> None:
        if self._stack is not None:
            await self._stack.aclose()
            self._stack = None
            self._session = None

    async def _elicit(self, context: Any, params: ElicitRequestParams) -> ElicitResult:
        """Callback di conferma: mostra la domanda, legge Y/N, registra l'esito.

        Il server (mcp_server.py) chiama ctx.elicit per i tool di scrittura.
        Torniamo action="accept" con confirm True/False; con N il server
        risponde cancelled e il modello deve avvisare l'operatore.
        """
        message = getattr(params, "message", "") or ""
        prompt = f"\n[CONFERMA] {message} [S/N] "

        conferma: bool | None = None
        for _ in range(MAX_CONFIRM_ATTEMPTS):
            try:
                # to_thread: input() e' bloccante e non deve fermare il loop.
                raw = await asyncio.to_thread(self.ask, prompt)
            except (EOFError, KeyboardInterrupt):
                raw = ""
            conferma = _parseAnswer(raw)
            if conferma is not None:
                break
            print("Rispondi S (procedi) oppure N (annulla).")

        if conferma is None:
            logEvent(self.logFile, "conferma", domanda=message, esito="N",
                     motivo="risposta non valida")
            return ElicitResult(action="decline")

        logEvent(self.logFile, "conferma", domanda=message,
                 esito="Y" if conferma else "N")
        return ElicitResult(action="accept", content={"confirm": conferma})

    async def callTool(self, name: str, arguments: dict) -> Any:
        """Esegue un tool sul server MCP e restituisce il risultato decodificato.

        Il server restituisce JSON dentro blocchi di testo. Se il JSON non si
        decodifica, torna il testo grezzo. Se result.isError e' vero, solleva
        RuntimeError: agent.py lo conta come tool fallito.
        """
        if self._session is None:
            raise RuntimeError("McpToolClient non avviato: usa 'async with'")

        result = await self._session.call_tool(
            name,
            arguments,
            read_timeout_seconds=self.toolTimeoutSeconds,
        )
        text = "\n".join(
            block.text
            for block in result.content
            if getattr(block, "type", None) == "text"
            and isinstance(getattr(block, "text", None), str)
        )

        if getattr(result, "isError", False):
            raise RuntimeError(text or f"il tool {name} ha restituito un errore")

        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return text
