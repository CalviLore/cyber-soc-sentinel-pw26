from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class Message:
    role: str
    content: str | None = None
    toolCalls: list[ToolCall] = field(default_factory=list)
    toolCallId: str | None = None

    def __post_init__(self):
        if self.role not in ("system", "user", "assistant", "tool"):
            raise ValueError(f"role non valido: {self.role!r}")


@dataclass
class Usage:
    promptTokens: int = 0
    completionTokens: int = 0

    @property
    def totalTokens(self) -> int:
        return self.promptTokens + self.completionTokens


@dataclass
class LLMResponse:
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
    def __init__(self, message: str, statusCode: int | None = None):
        super().__init__(message)
        self.statusCode = statusCode


class TransientLLMError(LLMError):
    """Errore ritentabile (es. 429/5xx); retryAfterSeconds viene dal Retry-After."""

    def __init__(self, message: str, statusCode: int | None = None,
                 retryAfterSeconds: float | None = None):
        super().__init__(message, statusCode)
        self.retryAfterSeconds = retryAfterSeconds


class PermanentLLMError(LLMError):
    """Errore non ritentabile (es. richiesta scritta male)."""


class LLMClient(ABC):
    model: str

    @abstractmethod
    async def chat(self, messages: list[Message], tools: list[dict],
                temperature: float = 0.0) -> LLMResponse:
        """cosa devo inserire qua ? """
