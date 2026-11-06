"""Test della trascrizione: i passaggi dell'agente scritti come in un terminale."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agent import AgentResult
from trascrizione import formattaChiamata, righeSessione, separaPensiero, testoDa

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
                         "  [CONFERMA] Isolare l'IP 1.2.3.4? [Y/N] N (automatico)")
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

    def test_senza_testo_finale(self):
        vuoto = AgentResult("modello non disponibile", "", 1, 0, errore="429")
        testi = [t for _, t in righeSessione("x", [], vuoto)]
        self.assertIn("● (nessun testo finale)", testi)

    def test_testoDa_unisce_le_righe(self):
        self.assertEqual(testoDa([("", "a"), ("", "b")]), "a\nb\n")


if __name__ == "__main__":
    unittest.main()
