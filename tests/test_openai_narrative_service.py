import os
import unittest
from unittest.mock import patch

from src.services.openai_narrative_service import OpenAINarrativeService


class TestOpenAINarrativeService(unittest.TestCase):
    def test_resolve_api_key_accepts_both_env_var_names(self):
        with patch.dict(os.environ, {'OPEN_AI_API_KEY': 'legacy-key'}, clear=False):
            with patch.dict(os.environ, {'OPENAI_API_KEY': ''}, clear=False):
                self.assertEqual(OpenAINarrativeService.resolve_api_key(), 'legacy-key')

        with patch.dict(os.environ, {'OPENAI_API_KEY': 'current-key'}, clear=False):
            with patch.dict(os.environ, {'OPEN_AI_API_KEY': 'legacy-key'}, clear=False):
                self.assertEqual(OpenAINarrativeService.resolve_api_key(), 'current-key')

    def test_model_defaults_can_be_overridden_from_env(self):
        with patch.dict(
            os.environ,
            {
                'OPENAI_TURN_MODEL': 'gpt-test-turn',
                'OPENAI_MEMORY_MODEL': 'gpt-test-memory',
                'OPENAI_EMBEDDING_MODEL': 'text-embedding-test',
            },
            clear=False,
        ):
            service = OpenAINarrativeService(api_key='dummy')
            self.assertEqual(service.turn_model, 'gpt-test-turn')
            self.assertEqual(service.memory_model, 'gpt-test-memory')
            self.assertEqual(service.embedding_model, 'text-embedding-test')
            self.assertTrue(service.is_configured())


if __name__ == '__main__':
    unittest.main()
