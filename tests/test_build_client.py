"""Test di buildClient: provider, chiavi mancanti, riserva di Gemini, NVIDIA."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from llm.fallback import FallbackClient
from llm.openai_compatible import OpenAICompatibleClient
from run_agent import buildClient

ENV = {
    "GEMINI_API_KEY": "g", "GEMINI_BASE_URL": "http://g/v1", "GEMINI_MODEL": "gemini-x",
    "GEMINI_FALLBACK_MODEL": "gemma-y",
    "MISTRAL_API_KEY": "m", "MISTRAL_BASE_URL": "http://m/v1", "MISTRAL_MODEL": "mistral-z",
    "NVIDIA_API_KEY": "n", "NVIDIA_MODEL": "nvidia/nemotron-test",
    "OLLAMA_BASE_URL": "http://localhost:11434/v1", "OLLAMA_MODEL_GOOGLE": "gemma4:e4b",
}


class BuildClientTest(unittest.TestCase):
    def test_gemini_ha_la_riserva_di_default(self):
        client = buildClient("gemini", ENV)
        self.assertIsInstance(client, FallbackClient)
        self.assertEqual([c.model for c in client.clients], ["gemini-x", "gemma-y"])

    def test_senza_riserva_gemini_e_un_client_solo(self):
        client = buildClient("gemini", ENV, fallback=False)
        self.assertIsInstance(client, OpenAICompatibleClient)
        self.assertEqual(client.model, "gemini-x")

    def test_nvidia_usa_il_modello_del_env_e_l_url_predefinito(self):
        client = buildClient("nvidia", ENV)
        self.assertEqual(client.model, "nvidia/nemotron-test")
        self.assertIn("integrate.api.nvidia.com", str(client.client.base_url))

    def test_nvidia_il_modello_si_puo_sovrascrivere(self):
        self.assertEqual(buildClient("nvidia", ENV, "nvidia/altro").model, "nvidia/altro")

    def test_nvidia_senza_chiave_da_errore_chiaro(self):
        env = {k: v for k, v in ENV.items() if k != "NVIDIA_API_KEY"}
        with self.assertRaises(SystemExit) as ctx:
            buildClient("nvidia", env)
        self.assertIn("NVIDIA_API_KEY", str(ctx.exception))

    def test_provider_sconosciuto(self):
        with self.assertRaises(SystemExit):
            buildClient("foo", ENV)


if __name__ == "__main__":
    unittest.main()
