"""Esegue un singolo run dell'harness da riga di comando.

Esempi:
    python src/run_agent.py --provider gemini --request "Analizza i log..."
    python src/run_agent.py --provider mistral --answer yes --db data/soc.db

Il programma stampa il riassunto preso da AgentResult (non dal modello) e il
testo finale. Il log JSONL va in logs/ per impostazione predefinita.
"""
import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path

from dotenv import dotenv_values

from agent import formatSummary, runAgent
from llm.fallback import FallbackClient
from llm.openai_compatible import OpenAICompatibleClient
from mcp_client import McpToolClient

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REQUEST = "Analizza i log di rete e riporta le anomalie che trovi."


# Come chiedere al provider di esporre il ragionamento. Mistral lo manda da solo
# (blocco thinking). Se un modello non lo supporta il client toglie i parametri.
GEMINI_PENSIERO = {"extra_body": {"extra_body": {"google": {
    "thinking_config": {"include_thoughts": True}}}}}
OLLAMA_PENSIERO = {"reasoning_effort": "medium"}


def buildClient(provider: str, env: dict, model: str | None = None,
                fallback: bool = True):
    """Costruisce il client del provider scelto, leggendo base URL e chiave dal .env.

    fallback=False: niente modello di riserva (Gemini non passa a Gemma): se il
    modello non risponde il run fallisce invece di cambiare modello in silenzio.

    PENSIERO=0 nel .env non chiede il ragionamento ai modelli (meno token e tempo).
    """
    pensiero = env.get("PENSIERO", "1") != "0"
    if provider == "gemini":
        baseUrl, key = env.get("GEMINI_BASE_URL"), env.get("GEMINI_API_KEY")
        primario = model or env.get("GEMINI_MODEL")
        riserva = env.get("GEMINI_FALLBACK_MODEL")
        if not (baseUrl and key and primario):
            raise SystemExit("Mancano GEMINI_BASE_URL, GEMINI_API_KEY o GEMINI_MODEL nel .env")
        params = GEMINI_PENSIERO if pensiero else None
        clients = [OpenAICompatibleClient(baseUrl, key, primario, params)]
        if riserva and not model and fallback:
            clients.append(OpenAICompatibleClient(baseUrl, key, riserva, params))
        return FallbackClient(clients) if len(clients) > 1 else clients[0]

    if provider == "mistral":
        baseUrl = env.get("MISTRAL_BASE_URL")
        key = env.get("MISTRAL_API_KEY")
        nome = model or env.get("MISTRAL_MODEL")
        if not (baseUrl and key and nome):
            raise SystemExit("Mancano MISTRAL_BASE_URL, MISTRAL_API_KEY o MISTRAL_MODEL nel .env")
        return OpenAICompatibleClient(baseUrl, key, nome)

    if provider == "nvidia":
        # NVIDIA NIM (build.nvidia.com): endpoint compatibile OpenAI, chiave nvapi-...
        baseUrl = env.get("NVIDIA_BASE_URL") or "https://integrate.api.nvidia.com/v1"
        key = env.get("NVIDIA_API_KEY")
        nome = model or env.get("NVIDIA_MODEL")
        if not (key and nome):
            raise SystemExit("Mancano NVIDIA_API_KEY o NVIDIA_MODEL nel .env")
        return OpenAICompatibleClient(baseUrl, key, nome)

    if provider == "ollama":
        baseUrl = env.get("OLLAMA_BASE_URL")
        nome = model or env.get("OLLAMA_MODEL_GOOGLE")
        if not (baseUrl and nome):
            raise SystemExit("Mancano OLLAMA_BASE_URL o un modello Ollama nel .env")
        return OpenAICompatibleClient(baseUrl, None, nome,
                                      OLLAMA_PENSIERO if pensiero else None)

    raise SystemExit(f"Provider sconosciuto: {provider}")


def makeAsk(answer: str):
    """Restituisce il callback di conferma: interattivo oppure Y/N automatico."""
    if answer == "yes":
        def sempreSi(question: str) -> str:
            print(f"{question}S (automatico)", flush=True)
            return "S"
        return sempreSi
    if answer == "no":
        def sempreNo(question: str) -> str:
            print(f"{question}N (automatico)", flush=True)
            return "N"
        return sempreNo
    return input


def parseArgs(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Un run dell'harness Cyber-SOC Sentinel")
    parser.add_argument("--provider", choices=["gemini", "mistral", "nvidia", "ollama"],
                        default="gemini")
    parser.add_argument("--model", help="sovrascrive il modello del .env")
    parser.add_argument("--request", default=DEFAULT_REQUEST)
    parser.add_argument("--db", help="percorso SQLite (default: data/soc.db)")
    parser.add_argument("--log", help="percorso del log JSONL")
    parser.add_argument("--max-iterations", type=int, default=10)
    parser.add_argument("--tool-timeout", type=float, default=30.0)
    parser.add_argument("--answer", choices=["ask", "yes", "no"], default="ask",
                        help="conferma Y/N: interattiva oppure automatica")
    return parser.parse_args(argv)


async def main(args: argparse.Namespace) -> int:
    env = dotenv_values(ROOT / ".env")
    client = buildClient(args.provider, env, args.model)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    logPath = Path(args.log) if args.log else ROOT / "logs" / f"agent-{timestamp}.jsonl"
    logPath.parent.mkdir(parents=True, exist_ok=True)

    mcpEnv = {"FAULT_TIMEOUT": "0"}
    if args.db:
        mcpEnv["SOC_DB"] = str(Path(args.db).resolve())

    print(f"modello: {client.model}\nlog: {logPath}", flush=True)
    async with McpToolClient(env=mcpEnv, logFile=logPath,
                             ask=makeAsk(args.answer),
                             toolTimeoutSeconds=args.tool_timeout) as mcp:
        result = await runAgent(
            client, mcp.tools, mcp.callTool, args.request,
            maxIterations=args.max_iterations, logFile=logPath,
            toolTimeoutSeconds=args.tool_timeout,
        )

    print("\n=== RISULTATO ===")
    print(formatSummary(result))
    if result.testoFinale:
        print("\nTesto finale:\n" + result.testoFinale)
    return 0


if __name__ == "__main__":
    # Il modello puo' usare frecce e altri caratteri non presenti in cp1252.
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(asyncio.run(main(parseArgs())))
