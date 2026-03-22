import os
import unittest
from unittest.mock import patch

from src.services.openai_narrative_service import OpenAINarrativeService


class TestOpenAINarrativeService(unittest.TestCase):
    def test_resolve_api_key_accepts_both_env_var_names(self):
        with patch.dict(os.environ, {"OPEN_AI_API_KEY": "legacy-key", "OPENAI_API_KEY": ""}, clear=False):
            self.assertEqual(OpenAINarrativeService.resolve_api_key(), "legacy-key")

        with patch.dict(os.environ, {"OPENAI_API_KEY": "current-key", "OPEN_AI_API_KEY": "legacy-key"}, clear=False):
            self.assertEqual(OpenAINarrativeService.resolve_api_key(), "current-key")

    def test_model_defaults_can_be_overridden_from_env(self):
        with patch.dict(
            os.environ,
            {
                "OPENAI_TURN_MODEL": "gpt-test-turn",
                "OPENAI_MEMORY_MODEL": "gpt-test-memory",
                "OPENAI_EMBEDDING_MODEL": "text-embedding-test",
                "OPENAI_COMBAT_JUDGE_MODEL": "gpt-test-judge",
                "OPENAI_TIMEOUT_SECONDS": "12",
                "OPENAI_MAX_RETRIES": "2",
            },
            clear=False,
        ):
            service = OpenAINarrativeService(api_key="dummy")
            self.assertEqual(service.turn_model, "gpt-test-turn")
            self.assertEqual(service.memory_model, "gpt-test-memory")
            self.assertEqual(service.embedding_model, "text-embedding-test")
            self.assertEqual(service.combat_judge_model, "gpt-test-judge")
            self.assertEqual(service.request_timeout_seconds, 12.0)
            self.assertEqual(service.max_retries, 2)
            self.assertTrue(service.is_configured())

    def test_defaults_apply_without_env_overrides(self):
        with patch.dict(os.environ, {}, clear=True):
            service = OpenAINarrativeService(api_key="dummy")
            self.assertEqual(service.request_timeout_seconds, 20.0)
            self.assertEqual(service.max_retries, 1)

    def test_client_uses_openai_api_key_timeout_and_retries(self):
        captured = {}

        def fake_openai(**kwargs):
            captured.update(kwargs)
            return object()

        with patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY": "current-key",
                "OPENAI_TIMEOUT_SECONDS": "9.5",
                "OPENAI_MAX_RETRIES": "3",
            },
            clear=False,
        ):
            with patch("src.services.openai_narrative_service.OpenAI", side_effect=fake_openai):
                service = OpenAINarrativeService()
                service._get_client()

        self.assertEqual(captured["api_key"], "current-key")
        self.assertEqual(captured["timeout"], 9.5)
        self.assertEqual(captured["max_retries"], 3)


if __name__ == "__main__":
    unittest.main()
