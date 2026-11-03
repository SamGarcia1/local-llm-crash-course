"""Small baseline checks; no model download or native inference required."""

import unittest
from pathlib import Path
from unittest.mock import Mock, patch

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


ROOT = Path(__file__).resolve().parents[1]


class ConfigurationTests(unittest.TestCase):
    def test_chainlit_config_parses(self):
        with (ROOT / ".chainlit" / "config.toml").open("rb") as config_file:
            config = tomllib.load(config_file)
        self.assertEqual(config["project"]["allow_origins"], ["*"])
        self.assertEqual(config["UI"]["name"], "Alfred")


class StartupTests(unittest.TestCase):
    def test_chain_configuration_and_memory(self):
        # Import the actual app and libraries, but never load model weights.
        import langchain_app

        client = Mock(side_effect=lambda *args, **kwargs: iter(["Ready."]))
        with patch(
            "ctransformers.AutoModelForCausalLM.from_pretrained",
            return_value=client,
        ) as load_model:
            chain = langchain_app.build_llm_chain()

        load_model.assert_called_once_with(
            "zoltanctoth/orca_mini_3B-GGUF",
            model_type="llama",
            model_file="orca-mini-3b.q4_0.gguf",
            lib=None,
            max_new_tokens=128,
            temperature=0.7,
        )
        self.assertEqual(chain.invoke({"question": "My name is Sam."})["text"], "Ready.")
        chain.invoke({"question": "What is my name?"})
        prompt = client.call_args.args[0]
        self.assertIn("My name is Sam.", prompt)
        self.assertIn("Ready.", prompt)
        self.assertIn("What is my name?", prompt)

        chain.memory.clear()
        chain.invoke({"question": "Hello again."})
        self.assertNotIn("My name is Sam.", client.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
