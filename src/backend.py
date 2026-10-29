"""Back-end: operazioni sul DB SQLite. Non conosce MCP né il modello.

Ogni funzione restituisce un dict e non solleva mai eccezioni verso l'alto:
in caso di problema il dict contiene la chiave "error".
"""
import ipaddress
import sqlite3
from contextlib import closing
from datetime import datetime

from db import connetti

MAX_LIMIT = 500
SEVERITIES = ("Bassa", "Media", "Alta")  # gli stessi valori del CHECK in schema.sql
DEFAULT_OPERATOR = "soc-agent"


def _isValidIp(ip):
    """True solo per un IPv4 valido scritto come stringa."""
    if not isinstance(ip, str):
        return False
    try:
        ipaddress.IPv4Address(ip)
        return True
    except ValueError:
        return False


def _now():
    return datetime.now().isoformat(timespec="seconds")


def readLogs(ip=None, statusCode=None, limit=100):
    """Log di rete filtrati per IP e/o status code, dal più recente."""
    if ip is not None and not _isValidIp(ip):
        return {"error": "Invalid IP"}
    # bool è sottoclasse di int: True passerebbe come "1", lo escludiamo
    if statusCode is not None and (
            not isinstance(statusCode, int) or isinstance(statusCode, bool)):
        return {"error": "Invalid statusCode"}
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
        return {"error": "Invalid limit"}
    limit = min(limit, MAX_LIMIT)

    conditions, params = [], []
    if ip is not None:
        conditions.append("ip = ?")
        params.append(ip)
    if statusCode is not None:
        conditions.append("status_code = ?")
        params.append(statusCode)
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    try:
        with closing(connetti()) as conn:
            total = conn.execute(
                f"SELECT COUNT(*) FROM network_logs {where}", params
            ).fetchone()[0]
            rows = conn.execute(
                f"SELECT * FROM network_logs {where} "
                "ORDER BY timestamp DESC, id DESC LIMIT ?",
                params + [limit],
            ).fetchall()
    except sqlite3.Error as e:
        return {"error": f"Database error: {e}"}
    return {"total": total, "returned": len(rows), "logs": [dict(r) for r in rows]}


def checkReputation(ip):
    """Whitelist, threat intel e asset critico per un IP."""
    if not _isValidIp(ip):
        return {"error": "Invalid IP"}
    try:
        with closing(connetti()) as conn:
            wl = conn.execute(
                "SELECT motivo FROM ip_whitelist WHERE ip = ?", (ip,)).fetchone()
            ti = conn.execute(
                "SELECT score, motivo FROM threat_intel_db WHERE ip = ?", (ip,)
            ).fetchone()
            asset = conn.execute(
                "SELECT nome, critico FROM assets WHERE ip = ?", (ip,)).fetchone()
    except sqlite3.Error as e:
        return {"error": f"Database error: {e}"}
    return {
        "ip": ip,
        "whitelisted": wl is not None,
        "whitelistReason": wl["motivo"] if wl else None,
        "threatScore": ti["score"] if ti else None,
        "threatReason": ti["motivo"] if ti else None,
        "assetName": asset["nome"] if asset else None,
        "criticalAsset": bool(asset and asset["critico"]),
    }


def validateIsolation(ip, reason):
    """Controlli di isolateIp senza scrivere. None se l'isolamento è ammesso.

    Il server MCP la chiama prima di chiedere Y/N all'operatore, così non gli
    si fa confermare un'azione destinata a essere rifiutata.
    """
    if not _isValidIp(ip):
        return {"error": "Invalid IP"}
    if not isinstance(reason, str) or not reason.strip():
        return {"error": "Reason is required"}
    try:
        with closing(connetti()) as conn:
            asset = conn.execute(
                "SELECT nome FROM assets WHERE ip = ? AND critico = 1", (ip,)
            ).fetchone()
            if asset:
                return {"error": f"Critical asset ({asset['nome']}): cannot be isolated"}
            if conn.execute(
                    "SELECT 1 FROM isolated_ips WHERE ip = ?", (ip,)).fetchone():
                return {"error": "IP already isolated"}
    except sqlite3.Error as e:
        return {"error": f"Database error: {e}"}
    return None


def isolateIp(ip, reason, operator=DEFAULT_OPERATOR):
    """SCRITTURA: aggiunge l'IP a isolated_ips. Rifiuta gli asset critici."""
    error = validateIsolation(ip, reason)
    if error:
        return error
    try:
        with closing(connetti()) as conn, conn:  # commit, o rollback se fallisce
            conn.execute(
                "INSERT INTO isolated_ips (ip, motivo, timestamp, operatore) "
                "VALUES (?, ?, ?, ?)",
                (ip, reason.strip(), _now(), operator),
            )
    except sqlite3.IntegrityError:  # UNIQUE su ip: isolato nel frattempo da altri
        return {"error": "IP already isolated"}
    except sqlite3.Error as e:
        return {"error": f"Database error: {e}"}
    return {"isolated": True, "ip": ip}


def validateTicket(title, description, severity, relatedIp=None,
                   relatedStatusCode=None):
    """Controlli di openTicket senza scrivere. None se il ticket è ammesso."""
    if not isinstance(title, str) or not title.strip():
        return {"error": "Title is required"}
    if not isinstance(description, str) or not description.strip():
        return {"error": "Description is required"}
    if severity not in SEVERITIES:
        return {"error": f"Invalid severity (use one of: {', '.join(SEVERITIES)})"}
    if relatedIp is not None and not _isValidIp(relatedIp):
        return {"error": "Invalid IP"}
    if relatedStatusCode is not None and (
            not isinstance(relatedStatusCode, int)
            or isinstance(relatedStatusCode, bool)):
        return {"error": "Invalid statusCode"}
    return None


def openTicket(title, description, severity, relatedIp=None,
               relatedStatusCode=None):
    """SCRITTURA: apre un ticket di incidente."""
    error = validateTicket(title, description, severity, relatedIp,
                           relatedStatusCode)
    if error:
        return error
    try:
        with closing(connetti()) as conn, conn:
            cur = conn.execute(
                "INSERT INTO incident_tickets (titolo, descrizione, gravita, "
                "ip_correlato, status_code_correlato, timestamp) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (title.strip(), description.strip(), severity, relatedIp,
                 relatedStatusCode, _now()),
            )
            ticketId = cur.lastrowid
    except sqlite3.Error as e:
        return {"error": f"Database error: {e}"}
    return {"ticketId": ticketId, "status": "aperto"}
