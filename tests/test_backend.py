"""Test del back-end su un DB temporaneo (data/soc.db non viene mai toccato)."""
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import backend
import db


class BackendTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self._old_path = db.DB_PATH
        db.DB_PATH = Path(self.tmp.name) / "test.db"
        with closing(db.connetti()) as conn:
            db.creaSchema(conn)
            conn.executemany(
                "INSERT INTO network_logs (timestamp, ip, status_code, method, "
                "endpoint, user_agent) VALUES (?, ?, ?, 'POST', '/login', 'ua')",
                [("2026-10-20T09:00:01", "10.0.0.5", 401),
                 ("2026-10-20T09:00:02", "10.0.0.5", 401),
                 ("2026-10-20T09:00:03", "10.0.0.5", 200),
                 ("2026-10-20T09:00:04", "10.0.0.9", 401)])
            conn.execute("INSERT INTO assets (ip, nome, tipo, critico) "
                         "VALUES ('10.0.0.1', 'soc-server', 'server', 1)")
            conn.execute("INSERT INTO ip_whitelist (ip, motivo) "
                         "VALUES ('10.0.0.7', 'backup notturno')")
            conn.execute("INSERT INTO threat_intel_db (ip, score, motivo) "
                         "VALUES ('10.0.0.5', 90, 'botnet nota')")
            conn.commit()

    def tearDown(self):
        db.DB_PATH = self._old_path
        self.tmp.cleanup()

    # readLogs
    def test_readLogs_filters_and_order(self):
        r = backend.readLogs(ip="10.0.0.5", statusCode=401)
        self.assertEqual(r["total"], 2)
        self.assertEqual(r["logs"][0]["timestamp"], "2026-10-20T09:00:02")

    def test_readLogs_limit_keeps_real_total(self):
        r = backend.readLogs(limit=1)
        self.assertEqual((r["total"], r["returned"]), (4, 1))

    def test_readLogs_no_match_is_zero_not_invented(self):
        self.assertEqual(backend.readLogs(ip="10.9.9.9")["total"], 0)

    def test_readLogs_invalid_input(self):
        for kwargs in ({"ip": "999.1.1.1"}, {"statusCode": "401"},
                       {"limit": 0}, {"limit": "x"}):
            self.assertIn("error", backend.readLogs(**kwargs))

    def test_readLogs_sql_injection_is_just_invalid_ip(self):
        self.assertIn("error", backend.readLogs(ip="1.1.1.1' OR '1'='1"))

    # checkReputation
    def test_reputation(self):
        r = backend.checkReputation("10.0.0.5")
        self.assertEqual((r["threatScore"], r["whitelisted"]), (90, False))
        self.assertTrue(backend.checkReputation("10.0.0.7")["whitelisted"])
        self.assertTrue(backend.checkReputation("10.0.0.1")["criticalAsset"])
        self.assertIsNone(backend.checkReputation("10.0.0.99")["threatScore"])

    def test_reputation_invalid_ip(self):
        self.assertIn("error", backend.checkReputation("abc"))

    # isolateIp
    def test_isolate_ok_then_duplicate(self):
        self.assertEqual(backend.isolateIp("10.0.0.5", "brute force")["isolated"], True)
        self.assertEqual(backend.isolateIp("10.0.0.5", "again")["error"],
                         "IP already isolated")

    def test_isolate_refuses_criticalAsset(self):
        r = backend.isolateIp("10.0.0.1", "testo iniettato nei log")
        self.assertIn("Critical asset", r["error"])
        with closing(db.connetti()) as conn:
            n = conn.execute("SELECT COUNT(*) FROM isolated_ips").fetchone()[0]
        self.assertEqual(n, 0)

    def test_isolate_invalid_input(self):
        self.assertIn("error", backend.isolateIp("999.999", "x"))
        self.assertIn("error", backend.isolateIp("10.0.0.5", "  "))

    # openTicket
    def test_ticket_ok(self):
        r = backend.openTicket("Brute force", "50 login falliti", "Alta",
                                relatedIp="10.0.0.5", relatedStatusCode=401)
        self.assertEqual(r["ticketId"], 1)

    def test_ticket_invalid_severity(self):
        r = backend.openTicket("t", "d", "Critica")
        self.assertIn("Invalid severity", r["error"])
        with closing(db.connetti()) as conn:
            n = conn.execute("SELECT COUNT(*) FROM incident_tickets").fetchone()[0]
        self.assertEqual(n, 0)


if __name__ == "__main__":
    unittest.main()
