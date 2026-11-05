"""Test di OpenAICompatibleClient: nessuna rete, l'SDK è sostituito da un finto."""
import asyncio
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest import mock

import httpx2
import openai

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from llm import openai_compatible
from llm.base import Message, PermanentLLMError, ToolCall, TransientLLMError
from llm.openai_compatible import OpenAICompatibleClient

REQUEST = httpx2.Request("POST", "http://test/v1/chat/completions")


def sdkResponse(content=None, toolCalls=None, usage=(3, 2), model="m-risposto",
                finishReason="stop", choices=None):
    """Risposta finta nella forma che restituisce l'SDK."""
    message = NS(content=content, tool_calls=toolCalls)
    if choices is None:
        choices = [NS(message=message, finish_reason=finishReason)]
    return NS(
        choices=choices,
        usage=NS(prompt_tokens=usage[0], completion_tokens=usage[1]) if usage else None,
        model=model,
    )


def sdkToolCall(arguments, callId="c1", name="readLogs", extraContent=None):
    fields = {"id": callId, "function": NS(name=name, arguments=arguments)}
    if extraContent is not None:
        fields["extra_content"] = extraContent
    return NS(**fields)


def statusError(status, headers=None):
    response = httpx2.Response(status, headers=headers or {}, request=REQUEST)
    return openai.APIStatusError(f"errore {status}", response=response, body=None)


class FakeSdk:
    """Sostituisce client.chat.completions.create: restituisce o solleva in sequenza."""

    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.requests = []

    async def create(self, **request):
        self.requests.append(request)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def makeClient(outcomes):
    client = OpenAICompatibleClient("http://test/v1", None, "m")
    sdk = FakeSdk(outcomes)
    client.client = NS(chat=NS(completions=NS(create=sdk.create)))
    return client, sdk


def run(client, messages=None, tools=None):
    """Esegue chat() senza attese reali; restituisce (risposta, attese richieste)."""
    delays = []

    async def fakeSleep(seconds):
        delays.append(seconds)

    messages = messages or [Message("user", "ciao")]
    with mock.patch.object(openai_compatible.asyncio, "sleep", fakeSleep):
        return asyncio.run(client.chat(messages, tools or [])), delays


class RispostaTest(unittest.TestCase):
    def test_testoSemplice(self):
        client, _ = makeClient([sdkResponse(content="ok", finishReason="stop")])
        response, _ = run(client)
        self.assertEqual(response.content, "ok")
        self.assertFalse(response.hasToolCalls)
        self.assertEqual(response.model, "m-risposto")
        self.assertEqual(response.finishReason, "stop")
        self.assertEqual(response.usage.totalTokens, 5)
        self.assertGreaterEqual(response.latencySeconds, 0)

    def test_toolCallConArgomentiValidi(self):
        client, _ = makeClient([sdkResponse(toolCalls=[sdkToolCall('{"ip": "1.2.3.4"}')])])
        response, _ = run(client)
        self.assertEqual(response.toolCalls,
                         [ToolCall("c1", "readLogs", {"ip": "1.2.3.4"})])
        self.assertIsNone(response.toolCalls[0].invalidArguments)

    def test_argomentiVuotiDiventanoDictVuoto(self):
        client, _ = makeClient([sdkResponse(toolCalls=[sdkToolCall("")])])
        response, _ = run(client)
        self.assertEqual(response.toolCalls[0].arguments, {})
        self.assertIsNone(response.toolCalls[0].invalidArguments)

    def test_jsonRottoNonSollevaMaSegnala(self):
        client, _ = makeClient([sdkResponse(toolCalls=[sdkToolCall("{rotto")])])
        response, _ = run(client)
        self.assertEqual(response.toolCalls[0].arguments, {})
        self.assertEqual(response.toolCalls[0].invalidArguments, "{rotto")

    def test_jsonValidoMaNonOggettoVieneSegnalato(self):
        client, _ = makeClient([sdkResponse(toolCalls=[sdkToolCall("[1, 2]")])])
        response, _ = run(client)
        self.assertEqual(response.toolCalls[0].invalidArguments, "[1, 2]")

    def test_toolCallConservaExtraContentDelProvider(self):
        # Gemini mette la thought_signature in extra_content: senza, il giro
        # successivo di tool calling viene rifiutato con HTTP 400.
        extra = {"google": {"thought_signature": "firma"}}
        client, _ = makeClient([
            sdkResponse(toolCalls=[sdkToolCall('{"limit": 5}', extraContent=extra)])
        ])
        response, _ = run(client)
        self.assertEqual(response.toolCalls[0].extraContent, extra)

    def test_usageAssenteDiventaZero(self):
        client, _ = makeClient([sdkResponse(content="ok", usage=None)])
        response, _ = run(client)
        self.assertEqual(response.usage.totalTokens, 0)

    def test_contenutoAListaDiBlocchiTieneSoloIlTesto(self):
        # Forma osservata dal vivo con Mistral: un blocco thinking e uno text.
        blocks = [
            {"type": "thinking", "thinking": [{"type": "text", "text": "ragiono"}]},
            {"type": "text", "text": "ok"},
        ]
        client, _ = makeClient([sdkResponse(content=blocks)])
        response, _ = run(client)
        self.assertEqual(response.content, "ok")

    def test_contenutoAListaSenzaTestoDiventaStringaVuota(self):
        blocks = [{"type": "thinking", "thinking": []}]
        client, _ = makeClient([sdkResponse(content=blocks)])
        response, _ = run(client)
        self.assertEqual(response.content, "")

    def test_choicesVuotoERitentato(self):
        client, sdk = makeClient([sdkResponse(choices=[]), sdkResponse(content="ok")])
        response, _ = run(client)
        self.assertEqual(response.content, "ok")
        self.assertEqual(len(sdk.requests), 2)


class RichiestaTest(unittest.TestCase):
    def test_messaggiTradottiNelFormatoSdk(self):
        client, sdk = makeClient([sdkResponse(content="ok")])
        messages = [
            Message("system", "sei un SOC"),
            Message("user", "controlla"),
            Message("assistant", None, [ToolCall("c1", "readLogs", {"ip": "è"})]),
            Message("tool", "[]", toolCallId="c1"),
        ]
        run(client, messages)
        sent = sdk.requests[0]["messages"]
        self.assertEqual(sent[0], {"role": "system", "content": "sei un SOC"})
        self.assertEqual(sent[2]["content"], "")
        self.assertEqual(sent[2]["tool_calls"], [{
            "id": "c1",
            "type": "function",
            "function": {"name": "readLogs", "arguments": '{"ip": "è"}'},
        }])
        self.assertEqual(sent[3], {"role": "tool", "content": "[]", "tool_call_id": "c1"})

    def test_extraContentRimandatoNellaRichiesta(self):
        extra = {"google": {"thought_signature": "firma"}}
        client, sdk = makeClient([sdkResponse(content="ok")])
        messages = [
            Message("assistant", None, [
                ToolCall("c1", "readLogs", {"limit": 5}, extraContent=extra)
            ]),
        ]
        run(client, messages)
        sent = sdk.requests[0]["messages"][0]["tool_calls"][0]
        self.assertEqual(sent["extra_content"], extra)

    def test_messaggioToolSenzaIdEPermanente(self):
        client, sdk = makeClient([])
        with self.assertRaises(PermanentLLMError):
            run(client, [Message("tool", "[]")])
        self.assertEqual(sdk.requests, [])

    def test_toolConvertitiNelFormatoOpenAI(self):
        client, sdk = makeClient([sdkResponse(content="ok")])
        schema = {"type": "object", "properties": {"ip": {"type": "string"}}}
        run(client, tools=[{"name": "checkReputation", "description": "d",
                            "inputSchema": schema}])
        self.assertEqual(sdk.requests[0]["tools"], [{
            "type": "function",
            "function": {"name": "checkReputation", "description": "d",
                         "parameters": schema},
        }])

    def test_senzaToolIlCampoNonVieneMandato(self):
        client, sdk = makeClient([sdkResponse(content="ok")])
        run(client)
        self.assertNotIn("tools", sdk.requests[0])

    def test_temperaturaZeroFissaTopP(self):
        # Mistral rifiuta temperature=0 se top_p non e' 1 (errore 400 visto dal vivo).
        client, sdk = makeClient([sdkResponse(content="ok")])
        run(client)
        self.assertEqual(sdk.requests[0]["top_p"], 1.0)

    def test_temperaturaAltaNonToccaTopP(self):
        client, sdk = makeClient([sdkResponse(content="ok")])
        asyncio.run(client.chat([Message("user", "x")], [], temperature=0.7))
        self.assertNotIn("top_p", sdk.requests[0])

    def test_temperatureEModelloPassati(self):
        client, sdk = makeClient([sdkResponse(content="ok")])
        asyncio.run(client.chat([Message("user", "x")], [], temperature=0.3))
        self.assertEqual(sdk.requests[0]["temperature"], 0.3)
        self.assertEqual(sdk.requests[0]["model"], "m")


class ErroriETentativiTest(unittest.TestCase):
    def test_429RitentatoPoiRiesce(self):
        client, sdk = makeClient([statusError(429), sdkResponse(content="ok")])
        response, delays = run(client)
        self.assertEqual(response.content, "ok")
        self.assertEqual(len(sdk.requests), 2)
        self.assertEqual(delays, [2.0])

    def test_attesaCrescente(self):
        client, _ = makeClient([statusError(503), statusError(503), sdkResponse(content="ok")])
        _, delays = run(client)
        self.assertEqual(delays, [2.0, 4.0])

    def test_retryAfterHaLaPrecedenza(self):
        client, _ = makeClient([statusError(429, {"retry-after": "7"}),
                                sdkResponse(content="ok")])
        _, delays = run(client)
        self.assertEqual(delays, [7.0])

    def test_retryAfterNonNumericoSiIgnora(self):
        client, _ = makeClient([statusError(429, {"retry-after": "domani"}),
                                sdkResponse(content="ok")])
        _, delays = run(client)
        self.assertEqual(delays, [2.0])

    def test_dopoTreTentativiRilanciaTransient(self):
        client, sdk = makeClient([statusError(503)] * 3)
        with self.assertRaises(TransientLLMError) as ctx:
            run(client)
        self.assertEqual(len(sdk.requests), 3)
        self.assertEqual(ctx.exception.statusCode, 503)

    def test_400NonRitentato(self):
        client, sdk = makeClient([statusError(400)])
        with self.assertRaises(PermanentLLMError) as ctx:
            run(client)
        self.assertEqual(len(sdk.requests), 1)
        self.assertEqual(ctx.exception.statusCode, 400)

    def test_401NonRitentato(self):
        client, sdk = makeClient([statusError(401)])
        with self.assertRaises(PermanentLLMError):
            run(client)
        self.assertEqual(len(sdk.requests), 1)

    def test_timeoutERitentato(self):
        client, sdk = makeClient([openai.APITimeoutError(REQUEST), sdkResponse(content="ok")])
        response, _ = run(client)
        self.assertEqual(response.content, "ok")
        self.assertEqual(len(sdk.requests), 2)

    def test_connessioneFallitaERitentata(self):
        client, sdk = makeClient([openai.APIConnectionError(request=REQUEST),
                                  sdkResponse(content="ok")])
        response, _ = run(client)
        self.assertEqual(response.content, "ok")

    def test_408ERitentato(self):
        client, _ = makeClient([statusError(408), sdkResponse(content="ok")])
        response, _ = run(client)
        self.assertEqual(response.content, "ok")


if __name__ == "__main__":
    unittest.main()
