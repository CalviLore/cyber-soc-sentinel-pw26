"""Test della forma dati dei client LLM: nessuna rete, solo oggetti Python."""
import asyncio
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from llm.base import (
    LLMClient,
    LLMError,
    LLMResponse,
    Message,
    PermanentLLMError,
    ToolCall,
    TransientLLMError,
    Usage,
)


class MessageTest(unittest.TestCase):
    def test_roleValido(self):
        for role in ("system", "user", "assistant", "tool"):
            self.assertEqual(Message(role).role, role)

    def test_roleNonValido(self):
        with self.assertRaises(ValueError):
            Message("supervisor")

    def test_toolCallsNonCondivise(self):
        primo = Message("user")
        secondo = Message("user")
        primo.toolCalls.append(ToolCall("c1", "readLogs", {}))
        self.assertEqual(secondo.toolCalls, [])


class LLMResponseTest(unittest.TestCase):
    def test_vuota(self):
        self.assertFalse(LLMResponse().hasToolCalls)

    def test_conToolCall(self):
        risposta = LLMResponse(toolCalls=[ToolCall("c1", "readLogs", {"n": 1})])
        self.assertTrue(risposta.hasToolCalls)

    def test_usageNonCondiviso(self):
        primo, secondo = LLMResponse(), LLMResponse()
        primo.usage.promptTokens = 10
        self.assertEqual(secondo.usage.promptTokens, 0)


class UsageTest(unittest.TestCase):
    def test_totalTokens(self):
        self.assertEqual(Usage(10, 5).totalTokens, 15)


class ErroreTest(unittest.TestCase):
    def test_gerarchia(self):
        self.assertTrue(issubclass(TransientLLMError, LLMError))
        self.assertFalse(issubclass(PermanentLLMError, TransientLLMError))

    def test_attributi(self):
        errore = TransientLLMError("troppe richieste", 429, 1.5)
        self.assertEqual(errore.statusCode, 429)
        self.assertEqual(errore.retryAfterSeconds, 1.5)


class FintoClient(LLMClient):
    model = "finto"

    async def chat(self, messages, tools, temperature=0.0):
        return LLMResponse(content="ok", model=self.model)


class ClientTest(unittest.TestCase):
    def test_astrattaNonIstaziabile(self):
        with self.assertRaises(TypeError):
            LLMClient()

    def test_senzaChatNonIstaziabile(self):
        class SenzaChat(LLMClient):
            model = "x"

        with self.assertRaises(TypeError):
            SenzaChat()

    def test_clientConcreto(self):
        risposta = asyncio.run(FintoClient().chat([Message("user", "ciao")], []))
        self.assertEqual(risposta.content, "ok")
        self.assertEqual(risposta.model, "finto")


if __name__ == "__main__":
    unittest.main()
