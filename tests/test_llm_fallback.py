"""Test di FallbackClient: i client interni sono FakeLLMClient, nessuna rete."""
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
    TransientLLMError,
)
from llm.fake import FakeLLMClient
from llm.fallback import FallbackClient


def chat(client, temperature=0.0):
    return asyncio.run(client.chat([Message("user", "ciao")], [], temperature))


class FallbackTest(unittest.TestCase):
    def test_eUnLLMClient(self):
        self.assertIsInstance(FallbackClient([FakeLLMClient([])]), LLMClient)

    def test_listaVuotaNonValida(self):
        with self.assertRaises(ValueError):
            FallbackClient([])

    def test_modelloEQuelloDelPrimo(self):
        client = FallbackClient([FakeLLMClient([], model="gemini"),
                                 FakeLLMClient([], model="gemma")])
        self.assertEqual(client.model, "gemini")

    def test_primoRispondeSecondoNonVieneChiamato(self):
        primo = FakeLLMClient([LLMResponse(content="dal primo")])
        secondo = FakeLLMClient([LLMResponse(content="dal secondo")])
        response = chat(FallbackClient([primo, secondo]))
        self.assertEqual(response.content, "dal primo")
        self.assertEqual(len(secondo.calls), 0)

    def test_transientDelPrimoPassaAlSecondo(self):
        primo = FakeLLMClient([TransientLLMError("429", 429)])
        secondo = FakeLLMClient([LLMResponse(content="dal secondo", model="gemma")])
        response = chat(FallbackClient([primo, secondo]))
        self.assertEqual(response.content, "dal secondo")
        self.assertEqual(response.model, "gemma")
        self.assertEqual(len(primo.calls), 1)

    def test_passaAlTerzoSeFallisconoIPrimiDue(self):
        client = FallbackClient([
            FakeLLMClient([TransientLLMError("a")]),
            FakeLLMClient([TransientLLMError("b")]),
            FakeLLMClient([LLMResponse(content="dal terzo")]),
        ])
        self.assertEqual(chat(client).content, "dal terzo")

    def test_laRispostaDellaRiservaDicePercheEScattato(self):
        primo = FakeLLMClient([TransientLLMError("troppe richieste", 429)],
                              model="gemini")
        secondo = FakeLLMClient([LLMResponse(content="ok", model="gemma")],
                                model="gemma")
        response = chat(FallbackClient([primo, secondo]))
        self.assertIn("gemini non ha risposto (429)", response.fallback)
        self.assertIn("troppe richieste", response.fallback)

    def test_seRispondeIlPrimoNonCeNessunaNota(self):
        primo = FakeLLMClient([LLMResponse(content="ok")], model="gemini")
        secondo = FakeLLMClient([], model="gemma")
        self.assertIsNone(chat(FallbackClient([primo, secondo])).fallback)

    def test_conPiuRiserveLaNotaElencaTutteLeFallite(self):
        client = FallbackClient([
            FakeLLMClient([TransientLLMError("a", 503)], model="m1"),
            FakeLLMClient([TransientLLMError("b")], model="m2"),
            FakeLLMClient([LLMResponse(content="dal terzo")], model="m3"),
        ])
        nota = chat(client).fallback
        self.assertIn("m1 non ha risposto (503)", nota)
        self.assertIn("m2 non ha risposto (errore)", nota)

    def test_permanentNonFaScattareIlFallback(self):
        primo = FakeLLMClient([PermanentLLMError("400", 400)])
        secondo = FakeLLMClient([LLMResponse(content="dal secondo")])
        with self.assertRaises(PermanentLLMError):
            chat(FallbackClient([primo, secondo]))
        self.assertEqual(len(secondo.calls), 0)

    def test_fallisconoTuttiRilanciaLUltimoErrore(self):
        client = FallbackClient([
            FakeLLMClient([TransientLLMError("primo", 429)]),
            FakeLLMClient([TransientLLMError("ultimo", 503)]),
        ])
        with self.assertRaises(TransientLLMError) as ctx:
            chat(client)
        self.assertEqual(str(ctx.exception), "ultimo")
        self.assertEqual(ctx.exception.statusCode, 503)

    def test_ognunoRiceveGliStessiArgomenti(self):
        primo = FakeLLMClient([TransientLLMError("x")])
        secondo = FakeLLMClient([LLMResponse(content="ok")])
        chat(FallbackClient([primo, secondo]), temperature=0.4)
        self.assertEqual(primo.calls[0], secondo.calls[0])
        self.assertEqual(secondo.calls[0]["temperature"], 0.4)

    def test_ogniChiamataRicominciaDalPrimo(self):
        primo = FakeLLMClient([TransientLLMError("x"), LLMResponse(content="primo")])
        secondo = FakeLLMClient([LLMResponse(content="secondo")])
        client = FallbackClient([primo, secondo])
        self.assertEqual(chat(client).content, "secondo")
        self.assertEqual(chat(client).content, "primo")


if __name__ == "__main__":
    unittest.main()
