from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ToolCall:
    """Richiesta del modello di eseguire un tool, con gli argomenti già come dict.

    Se il modello ha mandato argomenti che non sono un JSON valido, arguments
    resta vuoto e invalidArguments contiene il testo grezzo: sta al ciclo
    agentico non eseguire il tool e dirlo al modello.

    extraContent conserva i campi proprietari del provider che vanno rimandati
    indietro nella chiamata successiva. Serve a Gemini, che mette qui la
    thought_signature del function call: senza, il secondo giro di tool
    calling viene rifiutato con HTTP 400.
    """
    id: str
    name: str
    arguments: dict
    invalidArguments: str | None = None
    extraContent: dict | None = None


@dataclass
class Message:
    """Un messaggio della conversazione.

    role è system, user, assistant o tool. toolCalls è usato solo dai messaggi
    assistant; toolCallId solo dai messaggi tool, per collegare il risultato
    alla richiesta a cui risponde.
    """
    role: str
    content: str | None = None
    toolCalls: list[ToolCall] = field(default_factory=list)
    toolCallId: str | None = None

    def __post_init__(self):
        if self.role not in ("system", "user", "assistant", "tool"):
            raise ValueError(f"role non valido: {self.role!r}")


@dataclass
class Usage:
    """Token consumati da una chiamata: in ingresso (prompt) e in uscita (completion)."""
    promptTokens: int = 0
    completionTokens: int = 0

    @property
    def totalTokens(self) -> int:
        return self.promptTokens + self.completionTokens


@dataclass
class LLMResponse:
    """Risposta del modello: testo oppure richieste di tool, più i dati per il log.

    model è il modello che ha risposto davvero (utile con il fallback).
    """
    content: str | None = None
    # default_factory per non condividere la lista tra risposte diverse
    toolCalls: list[ToolCall] = field(default_factory=list)
    usage: Usage = field(default_factory=Usage)
    model: str = ""
    finishReason: str = ""
    latencySeconds: float = 0.0

    @property
    def hasToolCalls(self) -> bool:
        return len(self.toolCalls) > 0


class LLMError(Exception):
    """Errore base delle chiamate al modello; statusCode è quello HTTP, se esiste."""

    def __init__(self, message: str, statusCode: int | None = None):
        super().__init__(message)
        self.statusCode = statusCode


class TransientLLMError(LLMError):
    """Errore passeggero (es. 429, 5xx, timeout): ha senso riprovare.

    retryAfterSeconds viene dall'header Retry-After, se il server lo manda.
    """

    def __init__(self, message: str, statusCode: int | None = None,
                 retryAfterSeconds: float | None = None):
        super().__init__(message, statusCode)
        self.retryAfterSeconds = retryAfterSeconds


class PermanentLLMError(LLMError):
    """Errore definitivo (es. richiesta sbagliata, chiave non valida): riprovare non serve."""


class LLMClient(ABC):
    """Interfaccia comune dei modelli: il ciclo agentico usa solo questa.

    Gemini, Mistral, Ollama, il client finto per i test e il fallback la
    implementano, così il ciclo non sa quale modello c'è dietro.
    """
    model: str

    @abstractmethod
    async def chat(self, messages: list[Message], tools: list[dict],
                temperature: float = 0.0) -> LLMResponse:
        """Manda la conversazione al modello e restituisce una sola risposta.

        Riceve i messaggi, gli schemi dei tool disponibili e la temperature.
        Restituisce un LLMResponse con il testo oppure le richieste di tool,
        più token usati, modello che ha risposto e tempo impiegato.
        Solleva TransientLLMError se l'errore si può ritentare (429, 5xx,
        timeout) e PermanentLLMError se non ha senso riprovare.
        """

