# Diario di sviluppo — Cyber-SOC Sentinel

Log cronologico: 2 righe per modulo chiuso.

## 2026-09-24
- Modulo: setup iniziale del repository.
- Note: Fase 0 avviata.

## 2026-10-25
- Modulo: Fase 1 — schema.sql (6 tabelle), db.py, simulatore.py a comandi (/scenario, /clear), schema ER in docs/er.md.
- Note: dati deterministici (seed 42, T0 20/10/2026 10:00). Installati faker, mcp, jsonschema nel venv.
- Modifica: IP degli attaccanti (brute force, multitool, injection) generati dal seed invece che fissi nel codice; aggiunti comandi /ip e /seed N al simulatore. Motivo: valutare l'agente sul comportamento, non sull'indirizzo.
- Modifica: tutti gli IP (anche whitelist, threat intel, asset interni) generati dal seed; quantita' di log casuali in range configurabili (RANGE_*); nuovo scenario di controllo /login-sbagliato. Il simulatore crea solo fatti, le risposte attese stanno solo nei test.
