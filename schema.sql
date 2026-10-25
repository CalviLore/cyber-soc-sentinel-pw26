-- Schema del DB di Cyber-SOC Sentinel (6 tabelle, vedi SCALETTA.md passo 8)

CREATE TABLE network_logs (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp    TEXT    NOT NULL,          -- ISO 8601, es. 2026-10-20T09:58:12
    ip           TEXT    NOT NULL,          -- IPv4 sorgente
    status_code  INTEGER NOT NULL,
    method       TEXT    NOT NULL,
    endpoint     TEXT    NOT NULL,
    user_agent   TEXT    NOT NULL           -- dato NON fidato (scenario 7)
);
CREATE INDEX idx_logs_ip     ON network_logs(ip);
CREATE INDEX idx_logs_status ON network_logs(status_code);

CREATE TABLE assets (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    ip       TEXT NOT NULL UNIQUE,
    nome     TEXT NOT NULL,
    tipo     TEXT NOT NULL,                 -- es. server, host amministrativo
    critico  INTEGER NOT NULL DEFAULT 0     -- 1 = non va mai isolato
);

CREATE TABLE ip_whitelist (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    ip      TEXT NOT NULL UNIQUE,
    motivo  TEXT NOT NULL
);

CREATE TABLE threat_intel_db (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    ip      TEXT NOT NULL UNIQUE,
    score   INTEGER NOT NULL CHECK (score BETWEEN 0 AND 100),
    motivo  TEXT NOT NULL
);

CREATE TABLE isolated_ips (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ip         TEXT NOT NULL UNIQUE,
    motivo     TEXT NOT NULL,
    timestamp  TEXT NOT NULL,
    operatore  TEXT NOT NULL
);

CREATE TABLE incident_tickets (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    titolo                 TEXT NOT NULL,
    descrizione            TEXT NOT NULL,
    gravita                TEXT NOT NULL CHECK (gravita IN ('Bassa', 'Media', 'Alta')),
    ip_correlato           TEXT,
    status_code_correlato  INTEGER,
    timestamp              TEXT NOT NULL,
    stato                  TEXT NOT NULL DEFAULT 'aperto'
);
