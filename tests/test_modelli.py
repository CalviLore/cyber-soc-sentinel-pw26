"""Test dell'elenco modelli della chat (/models)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from modelli import costruisci, elencoModelli, interpreta, nomeCarino, Voce

ENV = {
    "GEMINI_API_KEY": "g", "GEMINI_BASE_URL": "http://g/v1", "GEMINI_MODEL": "gemini-x",
    "GEMINI_FALLBACK_MODEL": "gemma-y",
    "MISTRAL_API_KEY": "m", "MISTRAL_BASE_URL": "http://m/v1", "MISTRAL_MODEL": "mistral-z",
    "OLLAMA_BASE_URL": "http://localhost:11434/v1",
}


class ElencoModelliTest(unittest.TestCase):
    def test_online_solo_con_la_chiave(self):
        voci = elencoModelli(ENV, ollama=lambda env: [])
        self.assertEqual([v.provider for v in voci], ["gemini", "mistral"])  # niente nvidia

    def test_locali_dopo_gli_online(self):
        voci = elencoModelli(ENV, ollama=lambda env: ["gemma4:e4b", "phi4-mini:latest"])
        self.assertEqual([v.provider for v in voci],
                         ["gemini", "mistral", "ollama", "ollama"])
        self.assertEqual(voci[2].origine, "sul tuo PC")
        self.assertEqual(voci[3].modello, "phi4-mini:latest")

    def test_ollama_spento_non_rompe(self):
        self.assertEqual(len(elencoModelli(ENV, ollama=lambda env: [])), 2)


class NomiTest(unittest.TestCase):
    def test_nomi_noti(self):
        self.assertEqual(nomeCarino("phi4-mini:latest"), "Phi-4 mini")
        self.assertEqual(nomeCarino("hf.co/nvidia/NVIDIA-Nemotron-3.5-Bolt-E4B-4GB:Q4_K_M"),
                         "Nemotron 3.5 Bolt E4B")

    def test_nome_sconosciuto_ripulito(self):
        self.assertEqual(nomeCarino("hf.co/acme/mio-modello-7b:Q4"), "Mio Modello 7B")

    def test_granite_ed_embedding_esclusi(self):
        from modelli import modelliOllama  # noqa: F401
        voci = elencoModelli(ENV, ollama=lambda env: ["gemma4:e4b"])
        self.assertTrue(all("granite" not in v.etichetta.lower() for v in voci))


class ScegliTest(unittest.TestCase):
    def setUp(self):
        self.voci = elencoModelli(ENV, ollama=lambda env: ["a:1"])

    def test_numero_valido(self):
        self.assertEqual(interpreta("3", self.voci).modello, "a:1")

    def test_non_valido(self):
        for r in ("", "0", "9", "ciao", "-1"):
            self.assertIsNone(interpreta(r, self.voci))

    def test_costruisci_con_config_mancante_da_valueerror(self):
        with self.assertRaises(ValueError):
            costruisci(Voce("nvidia", None, "NVIDIA"), {})

    def test_costruisci_ok(self):
        client = costruisci(Voce("mistral", None, "Mistral"), ENV)
        self.assertEqual(client.model, "mistral-z")


if __name__ == "__main__":
    unittest.main()
