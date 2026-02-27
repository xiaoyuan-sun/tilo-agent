from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest.mock import patch

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from llm.client import MockModel, build_model_from_env


class LlmClientTests(unittest.TestCase):
    def test_build_model_from_env_returns_mock_when_provider_missing(self) -> None:
        with patch("llm.client.load_dotenv") as mock_load_dotenv:
            with patch.dict(os.environ, {}, clear=True):
                model = build_model_from_env()
        self.assertIsInstance(model, MockModel)
        mock_load_dotenv.assert_called_once_with(override=False)

    def test_build_model_from_env_requires_model_name_for_real_provider(self) -> None:
        with patch("llm.client.load_dotenv"):
            with patch.dict(
                os.environ,
                {"AGENTSCOPE_MODEL": "openai", "AGENTSCOPE_API_KEY": "k"},
                clear=True,
            ):
                with self.assertRaises(ValueError):
                    build_model_from_env()

    def test_build_model_from_env_builds_openai_model(self) -> None:
        calls: list[dict] = []

        class FakeOpenAIChatModel:
            def __init__(self, **kwargs) -> None:
                calls.append(kwargs)

        with patch("llm.client.load_dotenv") as mock_load_dotenv:
            with patch("llm.client.OpenAIChatModel", FakeOpenAIChatModel):
                with patch.dict(
                    os.environ,
                    {
                        "AGENTSCOPE_MODEL": "openai",
                        "AGENTSCOPE_MODEL_NAME": "gpt-4o-mini",
                        "AGENTSCOPE_API_KEY": "k",
                        "AGENTSCOPE_BASE_URL": "https://example.com/v1",
                    },
                    clear=True,
                ):
                    model = build_model_from_env()

        self.assertIsInstance(model, FakeOpenAIChatModel)
        mock_load_dotenv.assert_called_once_with(override=False)
        self.assertEqual(calls[0]["model_name"], "gpt-4o-mini")
        self.assertEqual(calls[0]["api_key"], "k")
        self.assertEqual(calls[0]["stream"], False)
        self.assertEqual(calls[0]["client_kwargs"], {"base_url": "https://example.com/v1"})


if __name__ == "__main__":
    unittest.main()
