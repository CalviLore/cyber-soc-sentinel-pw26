"""Test del motore Chat: memoria tra le frasi, conferma Y/N, ambiente del server.

Usa FakeLLMClient (nessun token) e il server MCP vero su un DB temporaneo
(variabile SOC_DB): data/soc.db non viene toccato.
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
from agent import STOP_FINAL_ANSWER, STOP_MODEL_ERROR
from chat import Chat, _faultValue
from llm.base import LLMResponse, ToolCall, TransientLLMError
from llm.fake import FakeLLMClient

IP = "10.0.0.5"


def isolaIp():
    return LLMResponse(toolCalls=[ToolCall("c1", "isolateIp",
                                           {"ip": IP, "reason": "brute force"})])


class ChatTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dbPath = Path(self.tmp.name) / "test.db"
        self.logPath = Path(self.tmp.name) / "chat.jsonl"
        self._oldPath = db.DB_PATH
        db.DB_PATH = self.dbPath
        with closing(db.connetti()) as conn:
            db.creaSchema(conn)
            conn.commit()

    def tearDown(self):
        db.DB_PATH = self._oldPath
        self.tmp.cleanup()

    def chat(self, client, answer="Y"):
        return Chat(client, db=self.dbPath, ask=lambda q: answer,
                    logFile=self.logPath)

    def isolati(self):
        with closing(db.connetti()) as conn:
            return [r["ip"] for r in conn.execute("SELECT ip FROM isolated_ips")]

    def run_(self, scenario):
        return asyncio.run(asyncio.wait_for(scenario(), timeout=60))

    def test_la_seconda_frase_vede_la_prima(self):
        client = FakeLLMClient([LLMResponse(content="uno"),
                                LLMResponse(content="due")])

        async def scenario():
            async with self.chat(client) as chat:
                await chat.rispondi("prima")
                return await chat.rispondi("seconda")

        result = self.run_(scenario)
        ruoli = [m.role for m in client.calls[1]["messages"]]
        self.assertEqual(ruoli, ["system", "user", "assistant", "user"])
        self.assertEqual(result.testoFinale, "due")

    def test_azzera_riparte_dal_system_prompt(self):
        client = FakeLLMClient([LLMResponse(content="uno"),
                                LLMResponse(content="due")])

        async def scenario():
            async with self.chat(client) as chat:
                await chat.rispondi("prima")
                chat.azzera()
                self.assertEqual(chat.history, [])
                await chat.rispondi("seconda")

        self.run_(scenario)
        ruoli = [m.role for m in client.calls[1]["messages"]]
        self.assertEqual(ruoli, ["system", "user"])

    def test_conferma_si_scrive_nel_db(self):
        client = FakeLLMClient([isolaIp(), LLMResponse(content="isolato")])

        async def scenario():
            async with self.chat(client, answer="Y") as chat:
                return await chat.rispondi("isola")

        result = self.run_(scenario)
        self.assertEqual(result.motivoArresto, STOP_FINAL_ANSWER)
        self.assertEqual(self.isolati(), [IP])

    def test_conferma_no_non_scrive_e_il_log_la_registra(self):
        client = FakeLLMClient([isolaIp(), LLMResponse(content="annullato")])

        async def scenario():
            async with self.chat(client, answer="N") as chat:
                return await chat.rispondi("isola")

        self.run_(scenario)
        self.assertEqual(self.isolati(), [])
        eventi = [json.loads(r) for r in
                  self.logPath.read_text(encoding="utf-8").splitlines()]
        conferme = [e for e in eventi if e["event"] == "conferma"]
        self.assertEqual([e["esito"] for e in conferme], ["N"])

    def test_eventi_contiene_solo_l_ultima_richiesta(self):
        client = FakeLLMClient([isolaIp(), LLMResponse(content="isolato"),
                                LLMResponse(content="ok")])

        async def scenario():
            async with self.chat(client, answer="Y") as chat:
                await chat.rispondi("isola")
                primi = [e["event"] for e in chat.eventi]
                await chat.rispondi("grazie")
                secondi = [e["event"] for e in chat.eventi]
                return primi, secondi

        primi, secondi = self.run_(scenario)
        self.assertIn("tool_chiamato", primi)
        self.assertIn("conferma", primi)
        self.assertEqual(secondi, ["richiesta", "risposta", "fine"])

    def test_dopo_un_errore_del_modello_la_chat_continua(self):
        client = FakeLLMClient([TransientLLMError("429"),
                                LLMResponse(content="ora risponde")])

        async def scenario():
            async with self.chat(client) as chat:
                primo = await chat.rispondi("prima")
                secondo = await chat.rispondi("riprovo")
                return primo, secondo

        primo, secondo = self.run_(scenario)
        self.assertEqual(primo.motivoArresto, STOP_MODEL_ERROR)
        self.assertEqual(secondo.motivoArresto, STOP_FINAL_ANSWER)
        self.assertEqual(secondo.testoFinale, "ora risponde")

    def test_al_server_passano_solo_db_e_fault(self):
        # Le chiavi API del .env non devono arrivare al server MCP.
        client = FakeLLMClient([])

        async def scenario():
            async with self.chat(client) as chat:
                return dict(chat.mcp.env)

        env = self.run_(scenario)
        self.assertEqual(set(env), {"FAULT_TIMEOUT", "SOC_DB"})

    def test_rispondi_senza_async_with_da_errore(self):
        chat = self.chat(FakeLLMClient([]))
        with self.assertRaises(RuntimeError):
            asyncio.run(chat.rispondi("ciao"))


class FaultValueTest(unittest.TestCase):
    def test_valori(self):
        for valore in (None, False, "", "0", "off", "No"):
            self.assertEqual(_faultValue(valore), "0", valore)
        for valore in (True, "1", "on", "timeout", "TRUE"):
            self.assertEqual(_faultValue(valore), "1", valore)


if __name__ == "__main__":
    unittest.main()
