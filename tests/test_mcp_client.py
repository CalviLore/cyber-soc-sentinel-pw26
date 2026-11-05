"""Test del client MCP stdio: avvia mcp_server.py e prova callTool e conferma Y/N.

Usa un DB temporaneo (variabile SOC_DB), data/soc.db non viene toccato.
"""
import asyncio
import json
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

SRC = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(SRC))

import db
from agent import runAgent
from llm.base import LLMResponse, ToolCall
from llm.fake import FakeLLMClient
from mcp_client import McpToolClient


class McpClientTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dbPath = Path(self.tmp.name) / "test.db"
        self.logPath = Path(self.tmp.name) / "run.jsonl"
        self._oldPath = db.DB_PATH
        db.DB_PATH = self.dbPath
        with closing(db.connetti()) as conn:
            db.creaSchema(conn)
            conn.execute(
                "INSERT INTO network_logs (timestamp, ip, status_code, method, "
                "endpoint, user_agent) VALUES ('2026-10-20T09:00:01', '10.0.0.5', "
                "401, 'POST', '/login', 'ua')")
            conn.execute("INSERT INTO assets (ip, nome, tipo, critico) "
                         "VALUES ('10.0.0.1', 'soc-server', 'server', 1)")
            conn.commit()

    def tearDown(self):
        db.DB_PATH = self._oldPath
        self.tmp.cleanup()

    def client(self, answer="Y", timeout=10.0):
        return McpToolClient(
            env={"SOC_DB": str(self.dbPath), "FAULT_TIMEOUT": "0"},
            logFile=self.logPath,
            ask=lambda prompt: answer,
            toolTimeoutSeconds=timeout,
        )

    def test_legge_i_quattro_tool_e_chiama_readLogs(self):
        async def scenario():
            async with self.client() as mcp:
                self.assertEqual(
                    {tool["name"] for tool in mcp.tools},
                    {"readLogs", "checkReputation", "isolateIp", "openTicket"},
                )
                self.assertTrue(all(tool["inputSchema"] for tool in mcp.tools))
                return await mcp.callTool("readLogs", {"ip": "10.0.0.5"})

        data = asyncio.run(asyncio.wait_for(scenario(), timeout=30))
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["logs"][0]["ip"], "10.0.0.5")

    def test_conferma_no_non_scrive_e_finisce_nel_log(self):
        async def scenario():
            async with self.client(answer="N") as mcp:
                return await mcp.callTool(
                    "isolateIp", {"ip": "10.0.0.5", "reason": "brute force"})

        data = asyncio.run(asyncio.wait_for(scenario(), timeout=30))
        self.assertTrue(data["cancelled"])
        self.assertEqual(self.countRows("isolated_ips"), 0)

        events = self.readLog()
        conferme = [e for e in events if e["event"] == "conferma"]
        self.assertEqual(len(conferme), 1)
        self.assertEqual(conferme[0]["esito"], "N")
        self.assertIn("10.0.0.5", conferme[0]["domanda"])

    def test_conferma_si_scrive_e_finisce_nel_log(self):
        async def scenario():
            async with self.client(answer="y") as mcp:
                return await mcp.callTool(
                    "isolateIp", {"ip": "10.0.0.5", "reason": "brute force"})

        data = asyncio.run(asyncio.wait_for(scenario(), timeout=30))
        self.assertTrue(data["isolated"])
        self.assertEqual(self.countRows("isolated_ips"), 1)

        conferme = [e for e in self.readLog() if e["event"] == "conferma"]
        self.assertEqual(conferme[0]["esito"], "Y")

    def test_runAgent_con_client_mcp_e_conferma_no(self):
        """Integrazione senza modello vero: FakeLLMClient + client MCP reale."""
        async def scenario():
            client = FakeLLMClient([
                LLMResponse(toolCalls=[ToolCall(
                    "c1", "isolateIp",
                    {"ip": "10.0.0.5", "reason": "brute force"})]),
                LLMResponse(content="operazione annullata dall'operatore"),
            ])
            async with self.client(answer="N") as mcp:
                return await runAgent(
                    client, mcp.tools, mcp.callTool,
                    "isola l'IP 10.0.0.5", logFile=self.logPath)

        result = asyncio.run(asyncio.wait_for(scenario(), timeout=30))
        self.assertEqual(result.toolRiusciti, 1)
        self.assertEqual(result.toolFalliti, 0)
        self.assertIn("annullata", result.testoFinale)
        self.assertEqual(self.countRows("isolated_ips"), 0)

        events = self.readLog()
        self.assertIn("conferma", [e["event"] for e in events])
        risultato = [e for e in events if e["event"] == "risultato"][0]
        self.assertEqual(risultato["esito"], "riuscito")
        self.assertIn('"cancelled": true', risultato["risultato"])

    def countRows(self, table):
        with closing(db.connetti()) as conn:
            return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    def readLog(self):
        return [json.loads(line)
                for line in self.logPath.read_text(encoding="utf-8").splitlines()]


if __name__ == "__main__":
    unittest.main()
