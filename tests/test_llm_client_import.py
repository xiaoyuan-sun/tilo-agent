from __future__ import annotations

import importlib
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


class LlmClientImportTests(unittest.TestCase):
    def test_import_client_without_agentscope_message_block(self) -> None:
        sys.modules.pop("llm.client", None)
        module = importlib.import_module("llm.client")
        self.assertTrue(hasattr(module, "MockModel"))


if __name__ == "__main__":
    unittest.main()
