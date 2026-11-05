import asyncio
import json
import time
from typing import Any

import openai
from openai import AsyncOpenAI

from .base import (
    LLMClient,
    LLMResponse,
    Message,
    PermanentLLMError,
    ToolCall,
    TransientLLMError,
    Usage,
)

MAX_ATTEMPTS = 3
BASE_DELAY_SECONDS = 2.0


def _retryAfterSeconds(response: Any) -> float | None:
    """Legge Retry-After (secondi) dalla risposta HTTP, se c'e' e se e' numerico."""
    if response is None:
        return None
    value = response.headers.get("retry-after")
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


class OpenAICompatibleClient(LLMClient):
    """Un solo client per tutti i provider che parlano il dialetto OpenAI.

    Gli errori ritentabili (429, 5xx, timeout, problemi di rete) vengono
    riprovati MAX_ATTEMPTS volte con attesa crescente; se anche l'ultimo
    tentativo fallisce l'errore viene rilanciato, cosi' il FallbackClient
    puo' passare al modello successivo.
    """

    def __init__(self, baseUrl: str, apiKey: str | None, model: str):
        self.model = model
        # Ollama non controlla la chiave, ma l'SDK ne pretende una non vuota.
        # max_retries=0: i tentativi li gestiamo qui, cosi' valgono le nostre attese
        # e il FallbackClient riceve l'errore dopo MAX_ATTEMPTS e non dopo molti di piu'.
        self.client = AsyncOpenAI(
            base_url=baseUrl, api_key=apiKey or "ollama", max_retries=0
        )

    async def chat(self, messages: list[Message], tools: list[dict],
                   temperature: float = 0.0) -> LLMResponse:
        sdkMessages = self._toSdkMessages(messages)

        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                return await self._call(sdkMessages, tools, temperature)
            except TransientLLMError as exc:
                if attempt == MAX_ATTEMPTS:
                    raise
                # Il Retry-After del provider ha la precedenza; altrimenti 2s, 4s...
                delay = exc.retryAfterSeconds
                if delay is None:
                    delay = BASE_DELAY_SECONDS * (2 ** (attempt - 1))
                await asyncio.sleep(delay)

    def _toSdkMessages(self, messages: list[Message]) -> list[dict]:
        """Traduce i Message del progetto nel formato atteso dall'SDK."""
        sdkMessages = []
        for msg in messages:
            item: dict[str, Any] = {"role": msg.role, "content": msg.content or ""}

            if msg.role == "tool":
                if not msg.toolCallId:
                    raise PermanentLLMError("messaggio tool senza toolCallId")
                item["tool_call_id"] = msg.toolCallId
            elif msg.toolCalls:
                item["tool_calls"] = []
                for tc in msg.toolCalls:
                    toolCall = {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            # L'SDK vuole gli arguments come stringa JSON.
                            "arguments": json.dumps(tc.arguments, ensure_ascii=False),
                        },
                    }
                    # Gemini (via endpoint OpenAI) pretende indietro la
                    # thought_signature del function call: senza, il secondo
                    # giro di tool calling fallisce con HTTP 400.
                    if tc.extraContent:
                        toolCall["extra_content"] = tc.extraContent
                    item["tool_calls"].append(toolCall)

            sdkMessages.append(item)
        return sdkMessages

    @staticmethod
    def _toSdkTools(tools: list[dict]) -> list[dict]:
        """Avvolge i tool (formato MCP: name, description, inputSchema) nel formato OpenAI."""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool["inputSchema"],
                },
            }
            for tool in tools
        ]

    async def _call(self, sdkMessages: list[dict], tools: list[dict],
                    temperature: float) -> LLMResponse:
        request: dict[str, Any] = {
            "model": self.model,
            "messages": sdkMessages,
            "temperature": temperature,
        }
        # Mistral rifiuta temperature=0 se top_p non e' 1. A temperatura 0 il
        # campionamento e' greedy, quindi top_p non cambia nulla: lo fissiamo.
        if temperature == 0:
            request["top_p"] = 1.0
        if tools:
            request["tools"] = self._toSdkTools(tools)

        started = time.perf_counter()
        try:
            response = await self.client.chat.completions.create(**request)
        except openai.APITimeoutError as exc:
            raise TransientLLMError(f"timeout: {exc}") from exc
        except openai.APIConnectionError as exc:
            raise TransientLLMError(f"connessione fallita: {exc}") from exc
        except openai.APIStatusError as exc:
            raise self._mapStatusError(exc) from exc
        except openai.OpenAIError as exc:
            raise PermanentLLMError(f"{type(exc).__name__}: {exc}") from exc
        latency = time.perf_counter() - started

        return self._toLLMResponse(response, latency)

    @staticmethod
    def _mapStatusError(exc: openai.APIStatusError) -> TransientLLMError | PermanentLLMError:
        """429, 408 e 5xx sono ritentabili; gli altri 4xx no."""
        status = exc.status_code
        detail = f"HTTP {status}: {exc}"
        # Il corpo del provider spiega il 400 (es. thought_signature mancante
        # in Gemini) meglio del solo codice: utile nel log e per il debug.
        try:
            body = (exc.response.text or "").strip()
        except Exception:
            body = ""
        if body:
            detail += f" | {body[:500]}"
        if status in (408, 429) or status >= 500:
            return TransientLLMError(detail, status, _retryAfterSeconds(exc.response))
        return PermanentLLMError(detail, status)

    @staticmethod
    def _textOf(content: Any) -> str | None:
        """Mistral manda il contenuto come lista di blocchi (thinking, text): tiene solo il testo."""
        if content is None or isinstance(content, str):
            return content
        parts = []
        for block in content:
            kind = block.get("type") if isinstance(block, dict) else getattr(block, "type", None)
            text = block.get("text") if isinstance(block, dict) else getattr(block, "text", None)
            if kind == "text" and isinstance(text, str):
                parts.append(text)
        return "".join(parts)

    def _toLLMResponse(self, response: Any, latency: float) -> LLMResponse:
        if not response.choices:
            raise TransientLLMError("risposta senza choices")
        choice = response.choices[0]
        message = choice.message

        toolCalls = []
        for tc in message.tool_calls or []:
            raw = tc.function.arguments or "{}"
            # Gemini mette qui la thought_signature del function call. Va
            # conservata e rimandata al giro successivo, altrimenti il
            # provider rifiuta la conversazione con HTTP 400.
            extraContent = getattr(tc, "extra_content", None)
            if extraContent is None:
                extraContent = (getattr(tc, "model_extra", None) or {}).get("extra_content")
            if not isinstance(extraContent, dict):
                extraContent = None

            # Un JSON rotto è un errore del modello, non del provider: non si
            # solleva, si segnala nella ToolCall e il ciclo agentico risponde al modello.
            try:
                arguments = json.loads(raw)
            except json.JSONDecodeError:
                arguments = None
            if isinstance(arguments, dict):
                toolCalls.append(ToolCall(id=tc.id, name=tc.function.name,
                                          arguments=arguments,
                                          extraContent=extraContent))
            else:
                toolCalls.append(ToolCall(id=tc.id, name=tc.function.name, arguments={},
                                          invalidArguments=raw,
                                          extraContent=extraContent))

        usage = response.usage
        return LLMResponse(
            content=self._textOf(message.content),
            toolCalls=toolCalls,
            usage=Usage(
                promptTokens=usage.prompt_tokens if usage else 0,
                completionTokens=usage.completion_tokens if usage else 0,
            ),
            model=response.model or self.model,
            finishReason=choice.finish_reason or "",
            latencySeconds=latency,
        )
