import json
import unittest
from unittest.mock import patch

from src.services.local_scene_description_service import LocalSceneDescriptionService


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def read(self):
        return json.dumps(self._payload).encode('utf-8')

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class TestLocalSceneDescriptionService(unittest.TestCase):
    def test_list_options_includes_expected_presets(self):
        service = LocalSceneDescriptionService()
        options = service.list_options()
        labels = [option.label for option in options]

        self.assertIn('Tracery (Built-in)', labels)
        self.assertIn('Ollama - qwen3:8b', labels)
        self.assertIn('Ollama - gemma3:12b', labels)
        self.assertIn('Ollama - gpt-oss:20b', labels)

    def test_default_runtime_option_prefers_first_ollama_model(self):
        service = LocalSceneDescriptionService(qwen_model='qwen3:8b')

        self.assertEqual(service.default_runtime_option_key(), 'ollama:qwen3:8b')

    @patch('src.services.local_scene_description_service.request.urlopen')
    def test_describe_scene_uses_ollama_chat_endpoint(self, mock_urlopen):
        mock_urlopen.return_value = _FakeResponse({'message': {'content': 'A tense goblin trail disappears into the trees.'}})
        service = LocalSceneDescriptionService(base_url='http://localhost:11434')

        description = service.describe_scene({'node': {'scene': 'test'}}, 'ollama:qwen3:8b')

        self.assertEqual(description, 'A tense goblin trail disappears into the trees.')
        args, kwargs = mock_urlopen.call_args
        request_obj = args[0]
        self.assertEqual(request_obj.full_url, 'http://localhost:11434/api/chat')
        self.assertEqual(kwargs['timeout'], service.timeout_seconds)

    @patch('src.services.local_scene_description_service.request.urlopen')
    def test_describe_scene_with_history_updates_state_and_dedupes(self, mock_urlopen):
        mock_urlopen.return_value = _FakeResponse(
            {'message': {'content': 'A rope bridge sways over black water. A rope bridge sways over black water. Smoke hangs under the canopy.'}}
        )
        service = LocalSceneDescriptionService(base_url='http://localhost:11434')
        prompt_packet = {
            'setting_context': {
                'biomeName': 'Goblin Jungle',
                'terrainName': 'Rope Walks',
                'climateName': 'Canopy Smoke',
                'settingContextTags': ['jungle', 'goblin'],
            },
            'node': {
                'node_id': 3,
                'role_name': 'Sentry Roost',
                'affordance_tags': ['high_ground'],
                'visible_features': [
                    {'feature_id': 'rope_bridge', 'category': 'structure', 'visible_labels': ['rope bridge']},
                ],
                'visible_hooks': [
                    {'hook_id': 'tracks', 'hook_type': 'CLUE', 'visible_text': 'Fresh goblin tracks cut across the bark.'},
                ],
            },
        }
        render_state = {
            'turn': 4,
            'recentSentenceTexts': ['A rope bridge sways over black water.'],
            'recentOpeningTexts': ['A rope bridge sways over black water.'],
            'recentFactKeys': ['feature:rope_bridge'],
            'recentNodeSignatures': [{'signature': 'older', 'turn': 4}],
            'factRecency': {'feature:rope_bridge': {'lastTurn': 4, 'uses': 2}},
        }

        result = service.describe_scene_with_history(prompt_packet, 'ollama:qwen3:8b', render_state=render_state)

        self.assertIn('Smoke hangs under the canopy.', result.text)
        self.assertLessEqual(result.text.count('A rope bridge sways over black water.'), 1)
        self.assertEqual(result.render_state['turn'], 5)
        self.assertTrue(result.render_state['recentNodeSignatures'])
        self.assertTrue(result.style_variant)

        args, _kwargs = mock_urlopen.call_args
        payload = json.loads(args[0].data.decode('utf-8'))
        self.assertIn('repeat_penalty', payload['options'])
        self.assertIn('typical_p', payload['options'])
        user_payload = json.loads(payload['messages'][1]['content'])
        self.assertIn('scene_plan', user_payload)
        self.assertIn('recent_avoidance', user_payload)

    def test_describe_scene_rejects_tracery_key(self):
        service = LocalSceneDescriptionService()
        with self.assertRaises(ValueError):
            service.describe_scene({'node': {}}, 'tracery')


if __name__ == '__main__':
    unittest.main()
