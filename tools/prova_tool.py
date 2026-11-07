"""Prova minima: un modello chiama un tool? Mostra anche se espone il ragionamento.

Manda una richiesta che richiede readLogs (con i veri schemi dei 4 tool del server MCP)
e stampa: tool chiamato, argomenti, ragionamento (se c'e'), token e secondi. Costa una
o due richieste: serve a valutare un modello prima di metterlo nel runner.

Uso:
    python tools/prova_tool.py nvidia                      # modello di NVIDIA_MODEL
    python tools/prova_tool.py nvidia --model nvidia/nemotron-3.5-super-vl-120b-a12b
    python tools/prova_tool.py ollama --model hf.co/nvidia/NVIDIA-Nemotron-3.5-Bolt-E4B-4GB:Q4_K_M
    python tools/prova_tool.py mistral
"""
import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from dotenv import dotenv_values

from agent import SYSTEM_PROMPT
from llm.base import LLMError, Message
from mcp_client import McpToolClient
from run_agent import buildClient

RICHIESTA = "Leggi i log dell'IP 203.0.113.7 filtrando solo gli errori 401."


async def main(args):
    env = dotenv_values(ROOT / ".env")
    client = buildClient(args.provider, env, args.model, fallback=False)
    print(f"modello: {client.model}")
    async with McpToolClient(env={"FAULT_TIMEOUT": "0"}) as mcp:
        messages = [Message("system", SYSTEM_PROMPT), Message("user", RICHIESTA)]
        try:
            r = await client.chat(messages, mcp.tools)
        except LLMError as exc:
            print(f"ERRORE: {type(exc).__name__}: {str(exc)[:600]}")
            return 1
    print(f"tempo: {r.latencySeconds:.1f} s · token: {r.usage.promptTokens} + "
          f"{r.usage.completionTokens} · fine: {r.finishReason} · ha risposto: {r.model}")
    if r.thinking:
        print(f"ragionamento ({len(r.thinking)} caratteri): {r.thinking[:300]!r}")
    else:
        print("ragionamento: non esposto")
    if r.content:
        print(f"testo: {r.content[:300]!r}")
    if r.toolCalls:
        for tc in r.toolCalls:
            stato = "ARGOMENTI ROTTI" if tc.invalidArguments else "ok"
            print(f"TOOL: {tc.name} {tc.arguments} [{stato}]")
        atteso = any(tc.name == "readLogs" and tc.arguments.get("ip") == "203.0.113.7"
                     and not tc.invalidArguments for tc in r.toolCalls)
        print("esito: " + ("PASSA (readLogs con l'IP giusto)" if atteso
                           else "tool chiamato ma non quello atteso"))
    else:
        print("esito: NESSUN TOOL CHIAMATO")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("provider", choices=["gemini", "mistral", "nvidia", "ollama"])
    p.add_argument("--model")
    raise SystemExit(asyncio.run(main(p.parse_args())))
