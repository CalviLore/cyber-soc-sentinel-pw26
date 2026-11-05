"""Client che ne contiene altri e li prova in ordine di preferenza.

Al ciclo agentico sembra un modello qualunque; dietro, se il primo non
risponde per un errore ritentabile, passa al successivo (es. Gemini -> Gemma).
"""
from .base import LLMClient, LLMResponse, Message, TransientLLMError


class FallbackClient(LLMClient):
    """Prova i client in ordine e restituisce la prima risposta ottenuta.

    Il fallback scatta solo su TransientLLMError (429, 5xx, timeout): i client
    interni hanno gia' fatto i loro tentativi, quindi qui non si ritenta lo
    stesso modello. I PermanentLLMError passano subito: una richiesta sbagliata
    fallirebbe su tutti, e una chiave non valida e' un errore di configurazione
    da vedere subito, non da nascondere con un altro modello.
    """

    def __init__(self, clients: list[LLMClient]):
        if not clients:
            raise ValueError("FallbackClient: serve almeno un client")
        self.clients = list(clients)
        # LLMClient richiede model: si usa quello del primo client, il preferito.
        self.model = self.clients[0].model

    async def chat(self, messages: list[Message], tools: list[dict],
                   temperature: float = 0.0) -> LLMResponse:
        lastError: TransientLLMError | None = None

        for client in self.clients:
            try:
                return await client.chat(messages, tools, temperature)
            except TransientLLMError as exc:
                lastError = exc

        # clients non e' vuota (controllato in __init__), quindi qui lastError c'e'.
        raise lastError
