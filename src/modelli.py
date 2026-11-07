"""Elenco dei modelli disponibili per la chat e scelta del modello.

Online: Gemini, Mistral e NVIDIA compaiono solo se nel .env c'e' la chiave.
Offline: si chiede a Ollama quali modelli sono scaricati (se Ollama e' spento
quelle voci semplicemente non ci sono). Contorno della chat: non ha niente a che
fare con il server MCP.
"""
import json
import urllib.request
from dataclasses import dataclass

from run_agent import buildClient

# Nomi che non sono modelli di chat, o che non usiamo
_ESCLUSI = ("embed", "granite")

# Nomi leggibili dei modelli del progetto (chiave: nome tecnico in minuscolo)
NOMI = {
    "gemini-3.6-flash": "Gemini 3.6 Flash",
    "gemma-4-31b-it": "Gemma 4 31B",
    "mistral-large-4": "Mistral Large 4",
    "nvidia/nemotron-3-ultra-550b-a55b": "Nemotron 3 Ultra 550B",
    "gemma4:e4b": "Gemma 4 E4B",
    "ministral-3:8b": "Ministral 3 8B",
    "phi4-mini:latest": "Phi-4 mini",
    "hf.co/nvidia/nvidia-nemotron-3.5-bolt-e4b-4gb:q4_k_m": "Nemotron 3.5 Bolt E4B",
}


def nomeCarino(modello):
    """Nome leggibile: dall'elenco NOMI, altrimenti il nome tecnico ripulito
    (senza percorso hf.co/, senza tag dopo i due punti, trattini in spazi)."""
    noto = NOMI.get(modello.lower())
    if noto:
        return noto
    base = modello.split("/")[-1].split(":")[0]
    return base.replace("-", " ").replace("_", " ").strip().title() or modello


@dataclass
class Voce:
    provider: str
    modello: str | None   # None = quello del .env
    etichetta: str        # nome leggibile
    origine: str = "online"   # "online" oppure "sul tuo PC"
    id: str = ""          # nome tecnico del modello (serve a segnare quello in uso)


def modelliOllama(env, timeout=2.0):
    """Nomi dei modelli scaricati in Ollama; lista vuota se Ollama non risponde."""
    base = (env.get("OLLAMA_BASE_URL") or "http://localhost:11434/v1").rstrip("/")
    if base.endswith("/v1"):
        base = base[:-3]
    try:
        with urllib.request.urlopen(base + "/api/tags", timeout=timeout) as r:
            dati = json.load(r)
    except (OSError, ValueError):
        return []
    nomi = [m.get("name", "") for m in dati.get("models", [])]
    return sorted(n for n in nomi if n and not any(x in n.lower() for x in _ESCLUSI))


def elencoModelli(env, ollama=modelliOllama):
    """Lista di Voce: prima gli online configurati, poi i locali scaricati.

    ollama: funzione che restituisce i nomi dei modelli locali (cambiabile nei test).
    """
    voci = []
    if env.get("GEMINI_API_KEY") and env.get("GEMINI_MODEL"):
        nome = nomeCarino(env["GEMINI_MODEL"])
        riserva = env.get("GEMINI_FALLBACK_MODEL")
        if riserva:
            nome += f" (riserva {nomeCarino(riserva)})"
        voci.append(Voce("gemini", None, nome, id=env["GEMINI_MODEL"]))
    if env.get("MISTRAL_API_KEY") and env.get("MISTRAL_MODEL"):
        voci.append(Voce("mistral", None, nomeCarino(env["MISTRAL_MODEL"]),
                         id=env["MISTRAL_MODEL"]))
    if env.get("NVIDIA_API_KEY") and env.get("NVIDIA_MODEL"):
        voci.append(Voce("nvidia", None, nomeCarino(env["NVIDIA_MODEL"]),
                         id=env["NVIDIA_MODEL"]))
    for nome in ollama(env):
        voci.append(Voce("ollama", nome, nomeCarino(nome), "sul tuo PC", id=nome))
    return voci


def costruisci(voce, env):
    """Client per la voce scelta. Se manca qualcosa nel .env: ValueError."""
    try:
        return buildClient(voce.provider, env, voce.modello)
    except SystemExit as exc:  # buildClient esce con un messaggio se manca la config
        raise ValueError(str(exc)) from None


def interpreta(risposta, voci):
    """Numero (1-based) -> Voce; None se vuoto o non valido."""
    risposta = risposta.strip()
    if risposta.isdigit() and 1 <= int(risposta) <= len(voci):
        return voci[int(risposta) - 1]
    return None


# Colore per famiglia, in esadecimale: ogni famiglia ha il suo (Gemini e Gemma,
# entrambi Google, condividono il blu). L'ordine conta: vale il primo che corrisponde.
COLORI_FAMIGLIA = [
    ("nemotron", "#76b900"),   # NVIDIA: verde
    ("mistral", "#ff7000"),    # Mistral: arancio
    ("ministral", "#ff7000"),  # "ministral" non contiene "mistral"
    ("gemini", "#4285f4"),     # Google: blu
    ("gemma", "#4285f4"),
    ("phi", "#b07cf0"),        # Microsoft: viola
]


def coloreModello(modello):
    """Colore (esadecimale) della famiglia del modello; None se non e' nell'elenco."""
    nome = (modello or "").lower()
    return next((c for chiave, c in COLORI_FAMIGLIA if chiave in nome), None)


def ansiColore(testo, esadecimale):
    """Testo col colore dato (truecolor ANSI); invariato se il colore e' None."""
    if not esadecimale:
        return testo
    r, g, b = (int(esadecimale[i:i + 2], 16) for i in (1, 3, 5))
    return f"\033[38;2;{r};{g};{b}m{testo}\033[0m"
