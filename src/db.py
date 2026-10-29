"""Accesso al database SQLite, condiviso da simulatore e server MCP."""
import os
import sqlite3
from pathlib import Path

SRC = Path(__file__).parent
BASE = SRC.parent  # radice del repo (qui sta data/)
DB_PATH = Path(os.environ.get("SOC_DB", BASE / "data" / "soc.db"))


def connetti():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def creaSchema(conn):
    """Ricrea da zero le 6 tabelle."""
    for t in ("network_logs", "assets", "ip_whitelist", "threat_intel_db",
              "isolated_ips", "incident_tickets"):
        conn.execute(f"DROP TABLE IF EXISTS {t}")
    conn.executescript((SRC / "schema.sql").read_text(encoding="utf-8"))
