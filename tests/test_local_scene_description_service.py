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

    def test_describe_scene_rejects_tracery_key(self):
        service = LocalSceneDescriptionService()
        with self.assertRaises(ValueError):
            service.describe_scene({'node': {}}, 'tracery')


if __name__ == '__main__':
    unittest.main()
