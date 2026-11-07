"""Test della trascrizione: i passaggi dell'agente scritti come in un terminale."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agent import AgentResult
from trascrizione import (formattaChiamata, logLeggibile, righeSessione,
                          separaPensiero, testoDa)

EVENTI = [
    {"event": "risposta", "testo": "Controllo i log dell'IP.",
     "toolCalls": ["readLogs"]},
    {"event": "tool_chiamato", "tool": "readLogs",
     "argomenti": {"ip": "1.2.3.4", "statusCode": 401, "limit": 25}},
    {"event": "risultato", "tool": "readLogs", "esito": "riuscito",
     "risultato": '{"total": 50,\n "returned": 25}'},
    {"event": "tool_chiamato", "tool": "isolateIp",
     "argomenti": {"ip": "1.2.3.4", "reason": "brute force"}},
    {"event": "conferma", "domanda": "Isolare l'IP 1.2.3.4?", "esito": "N"},
    {"event": "risultato", "tool": "isolateIp", "esito": "fallito",
     "risultato": "timeout"},
]
EVENTI_CON_MODELLO = [{"event": "risposta", "modello": "mistral-large-4",
                       "testo": None, "toolCalls": []}]
RISULTATO = AgentResult("risposta finale", "Operazione annullata.", 2, 100,
                        toolRiusciti=1, toolFalliti=1)


class TrascrizioneTest(unittest.TestCase):
    def stili(self, **opzioni):
        return righeSessione("domanda?", EVENTI, RISULTATO, **opzioni)

    def test_formatta_la_chiamata_con_i_parametri(self):
        self.assertEqual(formattaChiamata("readLogs", {"ip": "1.2.3.4", "limit": 25}),
                         'readLogs(ip="1.2.3.4", limit=25)')
        self.assertEqual(formattaChiamata("checkReputation", {}), "checkReputation()")

    def test_i_valori_lunghi_vengono_accorciati(self):
        riga = formattaChiamata("openTicket", {"description": "x" * 500})
        self.assertLess(len(riga), 100)
        self.assertIn("…", riga)

    def test_sessione_completa_nell_ordine_del_log(self):
        righe = self.stili()
        testi = [t for _, t in righe]
        self.assertEqual(testi[0], "> domanda?")  # nessun modello nel log
        self.assertEqual(righeSessione("x", EVENTI_CON_MODELLO, RISULTATO)[0][1],
                         "mistral-large-4> x")
        self.assertEqual(righeSessione("x", [], RISULTATO, modello="gemma")[0][1],
                         "gemma> x")
        self.assertEqual(testi[1], "● Controllo i log dell'IP.")
        self.assertEqual(testi[2], '● readLogs(ip="1.2.3.4", statusCode=401, limit=25)')
        self.assertEqual(testi[3], '  ⎿ riuscito: {"total": 50, "returned": 25}')
        self.assertEqual(testi[4], '● isolateIp(ip="1.2.3.4", reason="brute force")')
        self.assertEqual(testi[5],
                         "  [CONFERMA] Isolare l'IP 1.2.3.4? [S/N] N (automatico)")
        self.assertEqual(testi[6], "  ⎿ fallito: timeout")
        self.assertIn("● Operazione annullata.", testi)
        self.assertTrue(testi[-1].startswith("arresto: risposta finale | giri: 2"))

    def test_stili(self):
        stili = [s for s, _ in self.stili()]
        for atteso in ("prompt", "ragiona", "tool", "risultato", "conferma",
                       "errore", "risposta", "riepilogo"):
            self.assertIn(atteso, stili)

    def test_nella_chat_non_si_ripetono_domanda_e_conferma(self):
        testi = [t for _, t in self.stili(mostraRichiesta=False,
                                          mostraConferme=False, automatico=False)]
        self.assertFalse(any(t.startswith(">") for t in testi))
        self.assertFalse(any(t.startswith("mistral-large-4>") for t in testi))
        self.assertFalse(any("[CONFERMA]" in t for t in testi))

    def test_separa_il_pensiero_dalla_risposta(self):
        pensiero, risposta = separaPensiero(
            "<thought>Devo controllare i log.\nPoi rispondo.</thought>Tutto regolare.")
        self.assertEqual(pensiero, "Devo controllare i log.\nPoi rispondo.")
        self.assertEqual(risposta, "Tutto regolare.")
        self.assertEqual(separaPensiero("Solo risposta."), ("", "Solo risposta."))
        self.assertEqual(separaPensiero(None), ("", ""))
        # tag non chiuso: tutto il resto e' pensiero
        self.assertEqual(separaPensiero("<think>ragiono"), ("ragiono", ""))

    def test_senza_tool_ma_con_pensiero_in_grigio_e_risposta(self):
        risultato = AgentResult(
            "risposta finale",
            "<thought>Ho letto i log.</thought>Nessuna anomalia.", 3, 50)
        righe = righeSessione("x", EVENTI, risultato, mostraTool=False)
        testi = [t for _, t in righe]
        self.assertFalse(any(t.startswith("● readLogs") for t in testi))
        self.assertFalse(any("⎿" in t for t in testi))
        self.assertIn(("pensiero", "✻ Ho letto i log."), righe)
        self.assertIn(("risposta", "● Nessuna anomalia."), righe)
        # la conferma Y/N resta visibile
        self.assertTrue(any("[CONFERMA]" in t for t in testi))
        # niente tag nel testo mostrato
        self.assertFalse(any("<thought>" in t for t in testi))

    def test_stile_semplice_come_la_cli_di_ollama(self):
        risultato = AgentResult(
            "risposta finale",
            "<thought>Ho letto i log.</thought>Nessuna anomalia.", 3, 50)
        righe = righeSessione("ciao", EVENTI_CON_MODELLO, risultato, semplice=True,
                              mostraTool=False, mostraRiepilogo=False)
        testi = [t for _, t in righe]
        self.assertEqual(testi[0], ">>> ciao")  # nessun nome del modello nel prompt
        self.assertEqual(testi[testi.index("Thinking...") + 1], "Ho letto i log.")
        self.assertIn("...done thinking.", testi)
        self.assertEqual(testi[-1], "Nessuna anomalia.")  # risposta senza pallino
        self.assertFalse(any(t.startswith(("●", "✻")) for t in testi))

    def test_stile_semplice_raccoglie_le_note_del_modello_in_un_blocco(self):
        eventi = [
            {"event": "risposta", "testo": "Controllo i log.", "toolCalls": ["readLogs"]},
            {"event": "tool_chiamato", "tool": "readLogs", "argomenti": {}},
            {"event": "risposta", "testo": "Ora verifico la reputazione.",
             "toolCalls": ["checkReputation"]},
            {"event": "conferma", "domanda": "Isolare?", "esito": "N"},
        ]
        risultato = AgentResult("risposta finale", "Fatto.", 3, 10)
        testi = [t for _, t in righeSessione("ciao", eventi, risultato, semplice=True,
                                             mostraTool=False, mostraRiepilogo=False)]
        self.assertEqual(testi[0], ">>> ciao")
        self.assertEqual(testi[1], "Thinking...")
        self.assertEqual(testi[2], "Controllo i log.\nOra verifico la reputazione.")
        self.assertEqual(testi[3], "...done thinking.")
        self.assertEqual(testi.count("Thinking..."), 1)   # un solo blocco
        # il blocco viene prima della conferma e della risposta
        self.assertLess(testi.index("...done thinking."),
                        next(i for i, t in enumerate(testi) if "[CONFERMA]" in t))
        self.assertEqual(testi[-1], "Fatto.")

    def test_il_pensiero_del_log_va_nel_blocco_grigio(self):
        eventi = [
            {"event": "risposta", "testo": None, "toolCalls": ["readLogs"],
             "pensiero": "Devo leggere i log dell'IP."},
            {"event": "tool_chiamato", "tool": "readLogs", "argomenti": {}},
            {"event": "risposta", "testo": "Fatto.", "toolCalls": [],
             "pensiero": "I log confermano il brute force."},
        ]
        risultato = AgentResult("risposta finale", "Fatto.", 2, 10)
        testi = [t for _, t in righeSessione("ciao", eventi, risultato, semplice=True,
                                             mostraTool=False, mostraRiepilogo=False)]
        self.assertEqual(testi[1], "Thinking...")
        self.assertEqual(testi[2], "Devo leggere i log dell'IP.\nI log confermano il brute force.")
        self.assertEqual(testi[-1], "Fatto.")
        # nello stile completo il pensiero compare con il simbolo ✻, in ordine
        completo = [t for _, t in righeSessione("ciao", eventi, risultato)]
        self.assertIn("✻ Devo leggere i log dell'IP.", completo)

    def test_riepilogo_si_puo_nascondere(self):
        con = [t for _, t in righeSessione("x", EVENTI, RISULTATO)]
        senza = [t for _, t in righeSessione("x", EVENTI, RISULTATO,
                                             mostraRiepilogo=False)]
        self.assertTrue(con[-1].startswith("arresto:"))
        self.assertFalse(any(t.startswith("arresto:") for t in senza))
        self.assertEqual(senza[-1], "● Operazione annullata.")

    def test_log_leggibile_una_riga_per_evento(self):
        eventi = [
            {"ts": "2026-11-06T15:34:48.325+00:00", "event": "richiesta", "giro": 1,
             "nMessaggi": 2, "modello": "m1", "richiestaUtente": "Controlla."},
            {"ts": "2026-11-06T15:34:53.524+00:00", "event": "risposta", "giro": 1,
             "modello": "m1", "promptTokens": 100, "completionTokens": 20,
             "totalTokens": 120, "latenzaSecondi": 2.5, "testo": None,
             "toolCalls": ["readLogs"]},
            {"ts": "2026-11-06T15:34:53.527+00:00", "event": "tool_chiamato",
             "giro": 1, "tool": "readLogs", "argomenti": {"limit": 25}},
            {"ts": "2026-11-06T15:34:53.543+00:00", "event": "risultato", "giro": 1,
             "tool": "readLogs", "esito": "riuscito",
             "risultato": '{"total": 200, "returned": 25, "logs": [{"id": 1}, {"id": 2}]}'},
            {"ts": "2026-11-06T15:34:54+00:00", "event": "conferma",
             "domanda": "Isolare?", "esito": "N"},
            {"ts": "2026-11-06T15:34:55+00:00", "event": "risposta", "giro": 2,
             "modello": "m1", "promptTokens": 1, "completionTokens": 1,
             "totalTokens": 2, "latenzaSecondi": 1, "testo": "Prima riga.\n- punto uno",
             "toolCalls": []},
            {"ts": "2026-11-06T15:34:56+00:00", "event": "fine", "giro": 2,
             "motivo": "risposta finale", "tokenTotali": 122},
        ]
        testo = logLeggibile(eventi)
        righe = testo.splitlines()
        self.assertTrue(righe[0].startswith("ora"))
        self.assertTrue(any("RICHIESTA" in r and "modello m1" in r for r in righe))
        self.assertTrue(any("«Controlla.»" in r for r in righe))
        self.assertTrue(any("120 token (100 + 20)" in r and "chiede: readLogs" in r
                            for r in righe))
        self.assertTrue(any("TOOL" in r and "readLogs(limit=25)" in r for r in righe))
        # le righe di log dentro il risultato non si stampano: restano nel .jsonl
        self.assertTrue(any('{"total": 200, "returned": 25, "logs": […]}' in r
                            for r in righe))
        self.assertFalse(any('"id": 1' in r for r in righe))
        self.assertTrue(any("CONFERMA" in r and "Isolare? → N" in r for r in righe))
        # gli a-capo della risposta restano: ogni riga del modello sta a parte
        self.assertTrue(any(r.strip() == "Prima riga." for r in righe))
        self.assertTrue(any(r.strip() == "- punto uno" for r in righe))
        self.assertTrue(righe[-1].endswith("risposta finale · 122 token"))

    def test_il_log_leggibile_mostra_il_fallback(self):
        eventi = [{"ts": "2026-11-06T15:34:53+00:00", "event": "risposta", "giro": 1,
                   "modello": "gemma", "promptTokens": 1, "completionTokens": 1,
                   "totalTokens": 2, "latenzaSecondi": 1, "testo": "ok", "toolCalls": [],
                   "fallback": "gemini non ha risposto (503): sovraccarico"}]
        testo = logLeggibile(eventi)
        self.assertIn("FALLBACK: gemini non ha risposto (503): sovraccarico", testo)

    def test_senza_testo_finale(self):
        vuoto = AgentResult("modello non disponibile", "", 1, 0, errore="429")
        testi = [t for _, t in righeSessione("x", [], vuoto)]
        self.assertIn("● (nessun testo finale)", testi)

    def test_testoDa_unisce_le_righe(self):
        self.assertEqual(testoDa([("", "a"), ("", "b")]), "a\nb\n")


if __name__ == "__main__":
    unittest.main()
