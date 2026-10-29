"""Test end-to-end del server MCP: avvia il processo e lo interroga via stdio.

Usa un DB temporaneo (variabile SOC_DB), data/soc.db non viene toccato.
"""
import asyncio
import json
import os
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import ElicitResult

SRC = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(SRC))

import db

EXPECTED_TOOLS = {"readLogs", "checkReputation", "isolateIp", "openTicket"}


class McpServerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dbPath = Path(self.tmp.name) / "test.db"
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

    def run_session(self, scenario, answer=None):
        """Avvia il server, apre una sessione e esegue `scenario(session)`.

        `answer` simula l'operatore: True = Y, False = N, None = client che non
        supporta le richieste di conferma.
        """
        self.questions = []

        async def operator(context, params):
            self.questions.append(params.message)
            return ElicitResult(action="accept", content={"confirm": answer})

        callback = operator if answer is not None else None
        params = StdioServerParameters(
            command=sys.executable,
            args=[str(SRC / "mcp_server.py")],
            env={**os.environ, "SOC_DB": str(self.dbPath)},
        )

        async def main():
            async with stdio_client(params) as (read, write):
                async with ClientSession(
                        read, write, elicitation_callback=callback) as session:
                    await session.initialize()
                    return await scenario(session)

        return asyncio.run(asyncio.wait_for(main(), timeout=30))

    @staticmethod
    def payload(result):
        return json.loads(result.content[0].text)

    def test_lists_the_four_tools(self):
        async def scenario(session):
            return await session.list_tools()
        tools = self.run_session(scenario).tools
        self.assertEqual({t.name for t in tools}, EXPECTED_TOOLS)
        byName = {t.name: t for t in tools}
        self.assertTrue(byName["readLogs"].annotations.read_only_hint)
        self.assertFalse(byName["isolateIp"].annotations.read_only_hint)

    def test_read_logs_through_mcp(self):
        async def scenario(session):
            return await session.call_tool("readLogs", {"ip": "10.0.0.5"})
        data = self.payload(self.run_session(scenario))
        self.assertEqual(data["total"], 1)

    def test_write_tools_run_after_yes(self):
        async def scenario(session):
            ticket = await session.call_tool(
                "openTicket",
                {"title": "t", "description": "d", "severity": "Alta"})
            isolate = await session.call_tool(
                "isolateIp", {"ip": "10.0.0.5", "reason": "brute force"})
            return ticket, isolate
        ticket, isolate = self.run_session(scenario, answer=True)
        self.assertEqual(self.payload(ticket)["ticketId"], 1)
        self.assertTrue(self.payload(isolate)["isolated"])
        self.assertEqual(len(self.questions), 2)
        self.assertIn("10.0.0.5", self.questions[1])

    def test_write_tools_do_nothing_after_no(self):
        async def scenario(session):
            await session.call_tool(
                "isolateIp", {"ip": "10.0.0.5", "reason": "x"})
            return await session.call_tool(
                "openTicket",
                {"title": "t", "description": "d", "severity": "Alta"})
        result = self.run_session(scenario, answer=False)
        data = self.payload(result)
        self.assertTrue(data["cancelled"])
        self.assertNotIn("error", data)
        self.assertIn("tell the operator", data["message"])
        self.assertEqual(self.countRows("isolated_ips"), 0)
        self.assertEqual(self.countRows("incident_tickets"), 0)

    def test_write_tools_refuse_if_client_cannot_confirm(self):
        async def scenario(session):
            return await session.call_tool(
                "isolateIp", {"ip": "10.0.0.5", "reason": "x"})
        result = self.run_session(scenario, answer=None)
        self.assertIn("Confirmation unavailable", self.payload(result)["error"])
        self.assertEqual(self.countRows("isolated_ips"), 0)

    def test_invalid_requests_are_refused_before_asking(self):
        async def scenario(session):
            critical = await session.call_tool(
                "isolateIp", {"ip": "10.0.0.1", "reason": "testo iniettato"})
            badIp = await session.call_tool(
                "isolateIp", {"ip": "999.999", "reason": "x"})
            badTicket = await session.call_tool(
                "openTicket", {"title": " ", "description": "d", "severity": "Alta"})
            return critical, badIp, badTicket
        critical, badIp, badTicket = self.run_session(scenario, answer=True)
        self.assertIn("Critical asset", self.payload(critical)["error"])
        self.assertIn("Invalid IP", self.payload(badIp)["error"])
        self.assertIn("Title is required", self.payload(badTicket)["error"])
        self.assertEqual(self.questions, [])
        self.assertEqual(self.countRows("isolated_ips"), 0)

    def test_already_isolated_is_refused_before_asking(self):
        async def scenario(session):
            await session.call_tool("isolateIp", {"ip": "10.0.0.5", "reason": "a"})
            return await session.call_tool(
                "isolateIp", {"ip": "10.0.0.5", "reason": "b"})
        result = self.run_session(scenario, answer=True)
        self.assertEqual(self.payload(result)["error"], "IP already isolated")
        self.assertEqual(len(self.questions), 1)

    def test_read_tools_never_ask_for_confirmation(self):
        async def scenario(session):
            await session.call_tool("readLogs", {})
            await session.call_tool("checkReputation", {"ip": "10.0.0.5"})
        self.run_session(scenario, answer=True)
        self.assertEqual(self.questions, [])

    def countRows(self, table):
        with closing(db.connetti()) as conn:
            return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


if __name__ == "__main__":
    unittest.main()
