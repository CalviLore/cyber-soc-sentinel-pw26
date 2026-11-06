"""Test del ciclo agentico con FakeLLMClient e un callTool finto.

Nessuna rete e nessun server MCP: qui si prova solo la logica di agent.py.
"""
import asyncio
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agent import (
    STOP_FINAL_ANSWER,
    STOP_INTERRUPTED,
    STOP_MAX_ITERATIONS,
    STOP_MODEL_ERROR,
    SYSTEM_PROMPT,
    AgentResult,
    formatSummary,
    logEvent,
    runAgent,
)
from llm.base import (
    LLMClient,
    LLMResponse,
    Message,
    ToolCall,
    TransientLLMError,
    Usage,
)
from llm.fake import FakeLLMClient

TOOLS = [
    {
        "name": "readLogs",
        "description": "Legge i log di rete",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ip": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": [],
            "additionalProperties": False,
        },
    },
    {
        "name": "isolateIp",
        "description": "Isola un IP",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ip": {"type": "string"},
                "reason": {"type": "string"},
            },
            "required": ["ip", "reason"],
            "additionalProperties": False,
        },
    },
]


class FakeTools:
    """callTool finto: registra le chiamate e restituisce/raise quello che gli dici."""

    def __init__(self, result=None, error=None, delay=0.0):
        self.result = result if result is not None else {"ok": True}
        self.error = error
        self.delay = delay
        self.calls: list[tuple[str, dict]] = []

    async def __call__(self, name: str, arguments: dict):
        self.calls.append((name, arguments))
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.error is not None:
            raise self.error
        return self.result


class RaisingClient(LLMClient):
    """Client che solleva subito l'eccezione data (per CancelledError/KeyboardInterrupt)."""

    model = "raising"

    def __init__(self, exc: BaseException):
        self.exc = exc

    async def chat(self, messages, tools, temperature=0.0):
        raise self.exc


def run(client, tools=None, callTool=None, request="ciao", **kwargs):
    return asyncio.run(
        runAgent(client, TOOLS if tools is None else tools,
                 FakeTools() if callTool is None else callTool,
                 request, **kwargs)
    )


class CicloBaseTest(unittest.TestCase):
    def test_rispostaFinaleSubito(self):
        client = FakeLLMClient([
            LLMResponse(content="ok", usage=Usage(3, 2), model="fake-1"),
        ])
        tools = FakeTools()
        result = run(client, callTool=tools)

        self.assertIsInstance(result, AgentResult)
        self.assertEqual(result.motivoArresto, STOP_FINAL_ANSWER)
        self.assertEqual(result.testoFinale, "ok")
        self.assertEqual(result.giri, 1)
        self.assertEqual(result.tokenTotali, 5)
        self.assertEqual((result.toolRiusciti, result.toolFalliti,
                          result.toolRifiutati), (0, 0, 0))
        self.assertIsNone(result.errore)
        self.assertEqual(tools.calls, [])

        messages = client.calls[0]["messages"]
        self.assertEqual([m.role for m in messages], ["system", "user"])
        self.assertEqual(messages[0].content, SYSTEM_PROMPT)
        self.assertEqual(messages[1].content, "ciao")
        self.assertEqual(client.calls[0]["tools"], TOOLS)

    def test_laSecondaChiamataVedeIMessaggiDellaPrima(self):
        client = FakeLLMClient([
            LLMResponse(content="prima risposta", usage=Usage(1, 1)),
            LLMResponse(content="seconda risposta", usage=Usage(2, 1)),
        ])

        prima = run(client, request="prima domanda")
        seconda = run(client, request="seconda domanda",
                      history=prima.history)

        messaggi = client.calls[1]["messages"]
        self.assertEqual(
            [m.role for m in messaggi],
            ["system", "user", "assistant", "user"],
        )
        self.assertEqual(messaggi[0].content, SYSTEM_PROMPT)
        self.assertEqual(messaggi[1].content, "prima domanda")
        self.assertEqual(messaggi[2].content, "prima risposta")
        self.assertEqual(messaggi[3].content, "seconda domanda")
        # Il system prompt c'e' una volta sola: al secondo run non si duplica.
        self.assertEqual(sum(m.role == "system" for m in messaggi), 1)
        self.assertEqual(seconda.testoFinale, "seconda risposta")
        self.assertEqual(
            [m.role for m in seconda.history],
            ["system", "user", "assistant", "user", "assistant"],
        )

    def test_ilPromptDiSistemaDiceCheIToolSonoDati(self):
        self.assertIn("SOC", SYSTEM_PROMPT)
        self.assertIn("prompt injection", SYSTEM_PROMPT)
        self.assertIn("mai un'istruzione", SYSTEM_PROMPT)

    def test_tettoDiIterazioni(self):
        moves = [
            LLMResponse(toolCalls=[ToolCall(f"c{i}", "readLogs", {})],
                        usage=Usage(1, 1))
            for i in range(3)
        ]
        client = FakeLLMClient(moves)
        tools = FakeTools({"total": 0})
        result = run(client, callTool=tools, maxIterations=3)

        self.assertEqual(result.motivoArresto, STOP_MAX_ITERATIONS)
        self.assertEqual(result.giri, 3)
        self.assertEqual(result.tokenTotali, 6)
        self.assertEqual(result.toolRiusciti, 3)
        self.assertEqual(len(client.calls), 3)
        self.assertEqual(len(tools.calls), 3)
        # Alla terza chiamata ci sono i 2 messaggi iniziali e le coppie
        # assistant+tool dei due giri precedenti: 2 + 2 * 2 = 6.
        self.assertEqual(len(client.calls[-1]["messages"]), 6)

    def test_modelloNonDisponibile(self):
        client = FakeLLMClient([TransientLLMError("429 troppe richieste", 429)])
        result = run(client)

        self.assertEqual(result.motivoArresto, STOP_MODEL_ERROR)
        self.assertEqual(result.giri, 1)
        self.assertEqual(result.tokenTotali, 0)
        self.assertIn("429", result.errore)
        self.assertEqual(result.testoFinale, "")

    def test_interrottoConCancelledError(self):
        client = RaisingClient(asyncio.CancelledError())
        result = run(client)
        self.assertEqual(result.motivoArresto, STOP_INTERRUPTED)
        self.assertEqual(result.giri, 1)
        self.assertIn("CancelledError", result.errore)

    def test_interrottoConKeyboardInterrupt(self):
        client = RaisingClient(KeyboardInterrupt())
        result = run(client)
        self.assertEqual(result.motivoArresto, STOP_INTERRUPTED)
        self.assertIn("KeyboardInterrupt", result.errore)


class EsecuzioneToolTest(unittest.TestCase):
    def test_toolRiuscito(self):
        client = FakeLLMClient([
            LLMResponse(
                toolCalls=[ToolCall("c1", "readLogs", {"ip": "10.0.0.5"})],
                usage=Usage(10, 5),
            ),
            LLMResponse(content="fatto"),
        ])
        tools = FakeTools({"total": 1, "returned": 1})
        result = run(client, callTool=tools)

        self.assertEqual(result.motivoArresto, STOP_FINAL_ANSWER)
        self.assertEqual(result.giri, 2)
        self.assertEqual(result.tokenTotali, 15)
        self.assertEqual(result.toolRiusciti, 1)
        self.assertEqual(tools.calls, [("readLogs", {"ip": "10.0.0.5"})])

        messages = client.calls[1]["messages"]
        self.assertEqual([m.role for m in messages],
                         ["system", "user", "assistant", "tool"])
        toolMessage = messages[-1]
        self.assertEqual(toolMessage.toolCallId, "c1")
        self.assertIn("RISULTATO DEL TOOL readLogs", toolMessage.content)
        self.assertIn('"total": 1', toolMessage.content)

    def test_toolInesistenteRifiutatoSenzaEseguire(self):
        client = FakeLLMClient([
            LLMResponse(toolCalls=[ToolCall("c1", "rmRF", {})]),
            LLMResponse(content="non posso"),
        ])
        tools = FakeTools()
        result = run(client, callTool=tools)

        self.assertEqual(result.toolRifiutati, 1)
        self.assertEqual((result.toolRiusciti, result.toolFalliti), (0, 0))
        self.assertEqual(tools.calls, [])
        toolMessage = client.calls[1]["messages"][-1]
        self.assertEqual(toolMessage.role, "tool")
        self.assertEqual(toolMessage.toolCallId, "c1")
        self.assertIn("inesistente", toolMessage.content)
        self.assertIn("readLogs", toolMessage.content)

    def test_jsonDegliArgomentiRottoRifiutato(self):
        client = FakeLLMClient([
            LLMResponse(toolCalls=[
                ToolCall("c1", "readLogs", {}, invalidArguments="{rotto")
            ]),
            LLMResponse(content="correggo"),
        ])
        tools = FakeTools()
        result = run(client, callTool=tools)

        self.assertEqual(result.toolRifiutati, 1)
        self.assertEqual(tools.calls, [])
        self.assertIn("argomenti non validi",
                      client.calls[1]["messages"][-1].content)

    def test_argomentiFuoriSchemaRifiutati(self):
        client = FakeLLMClient([
            LLMResponse(toolCalls=[ToolCall("c1", "readLogs", {"ip": 123})]),
            LLMResponse(content="correggo"),
        ])
        tools = FakeTools()
        result = run(client, callTool=tools)

        self.assertEqual(result.toolRifiutati, 1)
        self.assertEqual(tools.calls, [])
        self.assertIn("argomenti non validi",
                      client.calls[1]["messages"][-1].content)

    def test_toolFallitoNonFermaIlCiclo(self):
        client = FakeLLMClient([
            LLMResponse(toolCalls=[
                ToolCall("c1", "readLogs", {"ip": "10.0.0.5"})
            ]),
            LLMResponse(content="il tool non risponde"),
        ])
        tools = FakeTools(error=RuntimeError("database bloccato"))
        result = run(client, callTool=tools)

        self.assertEqual(result.motivoArresto, STOP_FINAL_ANSWER)
        self.assertEqual(result.toolFalliti, 1)
        self.assertEqual(result.toolRiusciti, 0)
        toolMessage = client.calls[1]["messages"][-1]
        self.assertEqual(toolMessage.toolCallId, "c1")
        self.assertIn("database bloccato", toolMessage.content)

    def test_timeoutDelToolContaComeFallito(self):
        client = FakeLLMClient([
            LLMResponse(toolCalls=[
                ToolCall("c1", "readLogs", {"ip": "10.0.0.5"})
            ]),
            LLMResponse(content="timeout"),
        ])
        tools = FakeTools({"ok": True}, delay=0.5)
        result = run(client, callTool=tools, toolTimeoutSeconds=0.01)

        self.assertEqual(result.toolFalliti, 1)
        self.assertIn("timeout", client.calls[1]["messages"][-1].content)

    def test_ogniToolCallRiceveUnMessaggioTool(self):
        client = FakeLLMClient([
            LLMResponse(toolCalls=[
                ToolCall("c1", "readLogs", {}),
                ToolCall("c2", "rmRF", {}),
            ]),
            LLMResponse(content="fine"),
        ])
        result = run(client, callTool=FakeTools())

        self.assertEqual(result.toolRiusciti, 1)
        self.assertEqual(result.toolRifiutati, 1)
        messages = client.calls[1]["messages"]
        toolMessages = [m for m in messages if m.role == "tool"]
        self.assertEqual([m.toolCallId for m in toolMessages], ["c1", "c2"])


class LogTest(unittest.TestCase):
    def test_scriveUnaRigaJsonPerEvento(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "run.jsonl"
            client = FakeLLMClient([
                LLMResponse(
                    toolCalls=[ToolCall("c1", "readLogs", {"ip": "10.0.0.5"})],
                    usage=Usage(10, 5),
                    model="fake-1",
                ),
                LLMResponse(content="fatto", usage=Usage(2, 1),
                            model="fake-1"),
            ])
            result = run(client, callTool=FakeTools({"total": 1}),
                         logFile=path)

            self.assertEqual(result.motivoArresto, STOP_FINAL_ANSWER)
            lines = path.read_text(encoding="utf-8").splitlines()
            events = [json.loads(line) for line in lines]

        self.assertEqual(
            [e["event"] for e in events],
            ["richiesta", "risposta", "tool_chiamato", "risultato",
             "richiesta", "risposta", "fine"],
        )
        self.assertTrue(all("ts" in e for e in events))

        prima = events[0]
        self.assertEqual(prima["giro"], 1)
        self.assertEqual(prima["richiestaUtente"], "ciao")
        self.assertEqual(prima["tools"], ["isolateIp", "readLogs"])

        risposta = events[1]
        self.assertEqual(risposta["modello"], "fake-1")
        self.assertEqual(risposta["totalTokens"], 15)
        self.assertEqual(risposta["toolCalls"], ["readLogs"])

        chiamata = events[2]
        self.assertEqual(chiamata["tool"], "readLogs")
        self.assertEqual(chiamata["argomenti"], {"ip": "10.0.0.5"})

        risultato = events[3]
        self.assertEqual(risultato["esito"], "riuscito")
        self.assertIn('"total": 1', risultato["risultato"])

        fine = events[-1]
        self.assertEqual(fine["motivo"], STOP_FINAL_ANSWER)

    def test_logEventAccettaAncheUnFileAperto(self):
        import io
        buffer = io.StringIO()
        logEvent(buffer, "prova", valore=42)
        self.assertEqual(json.loads(buffer.getvalue())["valore"], 42)

    def test_senzaFileNonScriveNulla(self):
        logEvent(None, "prova")  # non deve sollevare

    def test_riassuntoNonUsaIlModello(self):
        result = AgentResult(
            motivoArresto=STOP_FINAL_ANSWER, testoFinale="x", giri=2,
            tokenTotali=10, toolRiusciti=1, toolFalliti=2, toolRifiutati=3,
        )
        riga = formatSummary(result)
        self.assertIn("risposta finale", riga)
        self.assertIn("1 riusciti", riga)
        self.assertIn("2 falliti", riga)
        self.assertIn("3 rifiutati", riga)


if __name__ == "__main__":
    unittest.main()
