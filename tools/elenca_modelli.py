"""Elenca i modelli disponibili per le chiavi cloud nel .env (Gemini, Mistral, NVIDIA).

Interroga GET {BASE_URL}/models e stampa gli id; per Mistral mostra anche quali
dichiarano il function calling. Non stampa mai le chiavi.

Uso:
    python tools/elenca_modelli.py                     # tutti i provider con chiave
    python tools/elenca_modelli.py nvidia              # solo NVIDIA
    python tools/elenca_modelli.py nvidia nemotron glm # solo gli id che contengono
                                                       # "nemotron" o "glm"
"""
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

from dotenv import dotenv_values

sys.stdout.reconfigure(encoding="utf-8")
env = dotenv_values(Path(__file__).resolve().parent.parent / ".env")

# nome -> (variabile della chiave, variabile dell'URL, URL predefinito)
PROVIDERS = {
    "Gemini": ("GEMINI_API_KEY", "GEMINI_BASE_URL", None),
    "Mistral": ("MISTRAL_API_KEY", "MISTRAL_BASE_URL", None),
    "NVIDIA": ("NVIDIA_API_KEY", "NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"),
}


def listModels(baseUrl, key):
    req = urllib.request.Request(
        baseUrl.rstrip("/") + "/models",
        headers={"Authorization": f"Bearer {key}", "User-Agent": "cyber-soc-sentinel"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def main(argv):
    scelto = argv[0].lower() if argv else None
    filtri = [f.lower() for f in argv[1:]]
    for name, (keyVar, urlVar, urlDefault) in PROVIDERS.items():
        if scelto and name.lower() != scelto:
            continue
        print(f"\n=== {name}")
        key, url = env.get(keyVar), env.get(urlVar) or urlDefault
        if not key or not url:
            print(f"{keyVar} o {urlVar} mancante nel .env")
            continue
        try:
            data = listModels(url, key)
        except urllib.error.HTTPError as e:
            print(f"Errore HTTP {e.code}: {e.reason}")
            continue
        except Exception as e:
            print(f"Errore: {type(e).__name__}: {e}")
            continue
        models = data.get("data", data.get("models", []))
        if filtri:
            models = [m for m in models if any(f in m.get("id", "").lower() for f in filtri)]
        for m in sorted(models, key=lambda m: m.get("id", "")):
            caps = m.get("capabilities") or {}
            tools = caps.get("function_calling")
            tag = "" if tools is None else ("  [tool: sì]" if tools else "  [tool: no]")
            print(f"{m.get('id')}{tag}")
        print(f"({len(models)} modelli)")


if __name__ == "__main__":
    main(sys.argv[1:])
