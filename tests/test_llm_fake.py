"""Test di FakeLLMClient: nessuna rete, restituisce solo quello che gli si dà."""
import asyncio
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from llm.base import (
    LLMClient,
    LLMResponse,
    Message,
    PermanentLLMError,
    ToolCall,
    TransientLLMError,
)
from llm.fake import FakeLLMClient


def chat(client, messages=None, tools=None, temperature=0.0):
    return asyncio.run(client.chat(messages or [Message("user", "ciao")], tools or [],
                                   temperature))


class RisposteTest(unittest.TestCase):
    def test_eUnLLMClient(self):
        self.assertIsInstance(FakeLLMClient([]), LLMClient)

    def test_modelloDiDefaultEPersonalizzato(self):
        self.assertEqual(FakeLLMClient([]).model, "fake")
        self.assertEqual(FakeLLMClient([], model="altro").model, "altro")

    def test_risposteInOrdine(self):
        primo = LLMResponse(toolCalls=[ToolCall("c1", "readLogs", {})])
        secondo = LLMResponse(content="fatto")
        client = FakeLLMClient([primo, secondo])
        self.assertIs(chat(client), primo)
        self.assertIs(chat(client), secondo)

    def test_eccezioneSollevataAlSuoTurno(self):
        client = FakeLLMClient([
            LLMResponse(content="a"),
            TransientLLMError("429", 429),
            PermanentLLMError("400", 400),
            LLMResponse(content="b"),
        ])
        self.assertEqual(chat(client).content, "a")
        with self.assertRaises(TransientLLMError):
            chat(client)
        with self.assertRaises(PermanentLLMError):
            chat(client)
        self.assertEqual(chat(client).content, "b")

    def test_mosseEsaurite(self):
        client = FakeLLMClient([LLMResponse(content="a")])
        chat(client)
        with self.assertRaises(RuntimeError) as ctx:
            chat(client)
        # Errore del test, non del provider: non deve passare per un LLMError.
        self.assertNotIsInstance(ctx.exception, (TransientLLMError, PermanentLLMError))

    def test_listaDelTestNonSvuotata(self):
        mosse = [LLMResponse(content="a"), LLMResponse(content="b")]
        client = FakeLLMClient(mosse)
        chat(client)
        chat(client)
        self.assertEqual(len(mosse), 2)


class RegistroChiamateTest(unittest.TestCase):
    def test_registraMessaggiToolETemperature(self):
        client = FakeLLMClient([LLMResponse(content="ok")])
        messages = [Message("user", "ciao")]
        tools = [{"name": "readLogs", "description": "d", "inputSchema": {}}]
        chat(client, messages, tools, temperature=0.3)
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(client.calls[0]["messages"], messages)
        self.assertEqual(client.calls[0]["tools"], tools)
        self.assertEqual(client.calls[0]["temperature"], 0.3)

    def test_ogniChiamataMostraLoStatoDiQuelMomento(self):
        client = FakeLLMClient([LLMResponse(content="a"), LLMResponse(content="b")])
        messages = [Message("user", "ciao")]
        chat(client, messages)
        messages.append(Message("assistant", "a"))  # il ciclo riusa la stessa lista
        chat(client, messages)
        self.assertEqual([len(c["messages"]) for c in client.calls], [1, 2])

    def test_registraAncheLaChiamataCheSollevaEQuellaDiTroppo(self):
        client = FakeLLMClient([TransientLLMError("429")])
        with self.assertRaises(TransientLLMError):
            chat(client)
        with self.assertRaises(RuntimeError):
            chat(client)
        self.assertEqual(len(client.calls), 2)


if __name__ == "__main__":
    unittest.main()
