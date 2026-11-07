import asyncio
import json
import re
import time
from typing import Any

import openai
from openai import AsyncOpenAI

from .pensiero import separaPensiero
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


def _chiamateDalTesto(testo: str, nomi) -> tuple[list[tuple[str, dict]], str]:
    """Cerca nel testo del modello chiamate ai tool scritte come JSON.

    Alcuni modelli piccoli (phi4-mini) scrivono la chiamata come testo, per esempio
    [{"name": "readLogs", "arguments": {"ip": "1.2.3.4"}}], invece che nel campo
    strutturato: il provider non la riconosce e il ciclo agentico la vedrebbe come
    risposta finale. Si accetta solo se TUTTE le voci hanno il nome di un tool che
    esiste e gli argomenti sono un oggetto: il resto del testo (anche un JSON
    qualsiasi) non viene toccato. Restituisce ([(nome, argomenti)], testo rimasto).
    """
    pulito = re.sub(r"<\|/?tool_call\|>", "", testo)
    decoder = json.JSONDecoder()
    i = 0
    while i < len(pulito):
        if pulito[i] not in "[{":
            i += 1
            continue
        try:
            valore, fine = decoder.raw_decode(pulito, i)
        except json.JSONDecodeError:
            i += 1
            continue
        voci = valore if isinstance(valore, list) else [valore]
        chiamate = []
        for voce in voci:
            if not isinstance(voce, dict):
                chiamate = []
                break
            nome = voce.get("name")
            args = voce.get("arguments", voce.get("parameters", {}))
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = None
            if nome not in nomi or not isinstance(args, dict):
                chiamate = []
                break
            chiamate.append((nome, args))
        if chiamate:
            return chiamate, (pulito[:i] + pulito[fine:]).strip()
        i = fine  # un JSON che non e' una chiamata ai tool: si va oltre
    return [], testo


def _parlaDiPensiero(exc: Exception) -> bool:
    """True se un errore 400 riguarda il ragionamento (modello che non lo supporta)."""
    testo = f"{exc} {getattr(exc, 'body', '')}".lower()
    return any(parola in testo for parola in ("thinking", "thought", "reasoning"))


def _testoDiBlocchi(valore: Any) -> str:
    """Testo di un blocco thinking: stringa oppure lista di blocchi {type: text}."""
    if isinstance(valore, str):
        return valore.strip()
    if isinstance(valore, list):
        testi = []
        for b in valore:
            testo = b.get("text") if isinstance(b, dict) else getattr(b, "text", None)
            if isinstance(testo, str):
                testi.append(testo.strip())
        return "\n".join(t for t in testi if t)
    return ""


class OpenAICompatibleClient(LLMClient):
    """Un solo client per tutti i provider che parlano il dialetto OpenAI.

    Gli errori ritentabili (429, 5xx, timeout, problemi di rete) vengono
    riprovati MAX_ATTEMPTS volte con attesa crescente; se anche l'ultimo
    tentativo fallisce l'errore viene rilanciato, cosi' il FallbackClient
    puo' passare al modello successivo.
    """

    def __init__(self, baseUrl: str, apiKey: str | None, model: str,
                 thinkingParams: dict | None = None):
        self.model = model
        # Parametri che chiedono al provider di esporre il ragionamento (cambiano da
        # provider a provider). Se il modello risponde che non li supporta si
        # tolgono e non si rimandano piu'.
        self.thinkingParams = dict(thinkingParams or {})
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
        request.update(self.thinkingParams)

        started = time.perf_counter()
        try:
            response = await self.client.chat.completions.create(**request)
        except openai.APITimeoutError as exc:
            raise TransientLLMError(f"timeout: {exc}") from exc
        except openai.APIConnectionError as exc:
            raise TransientLLMError(f"connessione fallita: {exc}") from exc
        except openai.APIStatusError as exc:
            if self.thinkingParams and exc.status_code == 400 and _parlaDiPensiero(exc):
                # il modello non supporta il ragionamento esposto: si riprova senza
                self.thinkingParams = {}
                return await self._call(sdkMessages, tools, temperature)
            raise self._mapStatusError(exc) from exc
        except openai.OpenAIError as exc:
            raise PermanentLLMError(f"{type(exc).__name__}: {exc}") from exc
        latency = time.perf_counter() - started

        return self._toLLMResponse(response, latency,
                                   {t["name"] for t in tools if "name" in t})

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
    def _pensieroDi(message: Any) -> str:
        """Ragionamento esposto dal provider: blocchi thinking (Mistral) o campo reasoning (Ollama)."""
        parti = []
        content = message.content
        if isinstance(content, list):
            for block in content:
                kind = block.get("type") if isinstance(block, dict) else getattr(block, "type", None)
                if kind == "thinking":
                    interno = (block.get("thinking") if isinstance(block, dict)
                               else getattr(block, "thinking", None))
                    parti.append(_testoDiBlocchi(interno))
        extra = getattr(message, "model_extra", None) or {}
        for campo in ("reasoning", "reasoning_content"):
            valore = getattr(message, campo, None) or extra.get(campo)
            if isinstance(valore, str) and valore.strip():
                parti.append(valore.strip())
        return "\n\n".join(p for p in parti if p)

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

    def _toLLMResponse(self, response: Any, latency: float,
                       toolNames=frozenset()) -> LLMResponse:
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

        toolDaTesto = False
        testo = self._textOf(message.content)
        pensieroTag = ""
        if testo is not None:
            pensieroTag, testo = separaPensiero(testo)  # Gemini/Gemma: <thought> nel testo
            if not toolCalls and testo and toolNames:
                # modelli che scrivono la chiamata come testo (phi4-mini)
                daTesto, testo = _chiamateDalTesto(testo, toolNames)
                for n, (nome, args) in enumerate(daTesto, 1):
                    toolCalls.append(ToolCall(id=f"testo-{n}", name=nome, arguments=args))
                toolDaTesto = bool(daTesto)
            if not testo and toolCalls:
                testo = None  # solo pensiero + tool: nessun testo da rimandare al modello
        pensiero = "\n\n".join(p for p in (self._pensieroDi(message), pensieroTag) if p) or None

        usage = response.usage
        return LLMResponse(
            content=testo,
            thinking=pensiero,
            toolDaTesto=toolDaTesto,
            toolCalls=toolCalls,
            usage=Usage(
                promptTokens=usage.prompt_tokens if usage else 0,
                completionTokens=usage.completion_tokens if usage else 0,
            ),
            model=response.model or self.model,
            finishReason=choice.finish_reason or "",
            latencySeconds=latency,
        )
