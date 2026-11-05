from .base import LLMClient, LLMResponse, Message


class FakeLLMClient(LLMClient):
    """Restituisce, in ordine, le risposte (o le eccezioni) che gli sono state date.

    Esempio:
        client = FakeLLMClient([
            LLMResponse(toolCalls=[ToolCall("c1", "readLogs", {})]),
            TransientLLMError("429"),
            LLMResponse(content="fatto"),
        ])
    """

    def __init__(self, moves: list[LLMResponse | Exception], model: str = "fake"):
        self.model = model
        # Copia: consumare le mosse non deve svuotare la lista del test.
        self.moves = list(moves)
        self.calls: list[dict] = []

    async def chat(self, messages: list[Message], tools: list[dict],
                   temperature: float = 0.0) -> LLMResponse:
        # Copia superficiale: il ciclo agentico di solito riusa la stessa lista
        # messages, quindi senza copia tutte le chiamate registrate mostrerebbero
        # lo stato finale invece di quello visto al momento della chiamata.
        self.calls.append({
            "messages": list(messages),
            "tools": list(tools),
            "temperature": temperature,
        })

        if not self.moves:
            raise RuntimeError(
                "FakeLLMClient: mosse esaurite, il test ha previsto meno chiamate"
            )

        move = self.moves.pop(0)
        if isinstance(move, Exception):
            raise move
        return move
