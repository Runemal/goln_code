import asyncio
import copy
import os
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch
from yandex_compat import proxy_handler_instance


class YandexHeadersTest(unittest.TestCase):
    def hook(self, data):
        return asyncio.run(proxy_handler_instance.async_pre_call_hook(None, None, data, 'aresponses'))

    def test_project_added_to_chat_responses_and_embeddings_without_mutation(self):
        with patch.dict(os.environ, {'YANDEX_FOLDER_ID': 'test-folder'}):
            for route in ('yandex/chat', 'yandex/lite', 'yandex/embeddings', 'yandex/embeddings-query'):
                data = {'model': route, 'input': 'synthetic', 'extra_headers': {'X-Custom': 'kept'}}
                original = copy.deepcopy(data)
                result = self.hook(data)
                self.assertEqual(result['extra_headers'], {'X-Custom': 'kept', 'OpenAI-Project': 'test-folder'})
                self.assertEqual(data, original)

    def test_other_providers_are_untouched(self):
        with patch.dict(os.environ, {}, clear=True):
            for route in ('nim/chat', 'cloudru/Qwen/Qwen3-Coder-Next', 'local/ollama'):
                data = {'model': route, 'input': 'synthetic'}
                self.assertIs(self.hook(data), data)

    def test_client_cannot_override_billing_project(self):
        with patch.dict(os.environ, {'YANDEX_FOLDER_ID': 'test-folder'}):
            result = self.hook({'model': 'yandex/chat', 'extra_headers': {'OpenAI-Project': 'other-folder'}})
            self.assertEqual(result['extra_headers']['OpenAI-Project'], 'test-folder')

    def test_missing_or_placeholder_folder_fails_before_upstream(self):
        for folder in ('', 'replace-with-folder-id', 'not-configured'):
            with patch.dict(os.environ, {'YANDEX_FOLDER_ID': folder}):
                with self.assertRaisesRegex(ValueError, 'YANDEX_FOLDER_ID'):
                    self.hook({'model': 'yandex/chat'})

    def test_paid_script_is_disabled_without_explicit_opt_in(self):
        script = Path(__file__).parent / 'test-yandex.sh'
        result = subprocess.run(['bash', str(script)], env={**os.environ, 'YANDEX_TEST_ALLOW_INFERENCE': '0'},
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('Платные проверки отключены', result.stderr)

    def test_paid_script_rejects_other_providers_before_reading_credentials(self):
        script = Path(__file__).parent / 'test-yandex.sh'
        result = subprocess.run(['bash', str(script), 'cloudru/Qwen/Qwen3-Coder-Next'],
                                env={**os.environ, 'YANDEX_TEST_ALLOW_INFERENCE': '1'}, text=True, capture_output=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('ровно один маршрут', result.stderr)


if __name__ == '__main__':
    unittest.main()
