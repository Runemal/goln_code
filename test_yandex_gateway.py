"""Exercise the real pinned gateway against a local fake Yandex API, without internet."""
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import threading
import time
import unittest
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import yaml


class FakeYandex(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        self.server.calls.append({'path': self.path, 'body': body,
                                  'authorization': self.headers.get('Authorization'),
                                  'project': self.headers.get('OpenAI-Project')})
        if self.path == '/v1/embeddings':
            result = {'object': 'list', 'model': body['model'], 'data': [
                {'object': 'embedding', 'index': 0, 'embedding': [0.25, 0.5, 0.75]}],
                'usage': {'prompt_tokens': 1, 'total_tokens': 1}}
        elif self.path == '/v1/chat/completions':
            if body.get('stream'):
                self.send_response(200)
                self.send_header('Content-Type', 'text/event-stream')
                self.end_headers()
                for delta, finish in [({'role': 'assistant', 'content': 'MOCK_OK'}, None), ({}, 'stop')]:
                    event = {'id': 'chatcmpl-mock', 'object': 'chat.completion.chunk', 'created': 1,
                             'model': body['model'], 'choices': [{'index': 0, 'delta': delta, 'finish_reason': finish}]}
                    self.wfile.write(('data: ' + json.dumps(event) + '\n\n').encode())
                self.wfile.write(b'data: [DONE]\n\n')
                self.wfile.flush()
                return
            message = {'role': 'assistant', 'content': 'MOCK_OK'}
            finish = 'stop'
            if body.get('tools'):
                message = {'role': 'assistant', 'content': None, 'tool_calls': [{
                    'id': 'call-mock', 'type': 'function',
                    'function': {'name': 'probe', 'arguments': '{"value":"OK"}'}}]}
                finish = 'tool_calls'
            result = {'id': 'chatcmpl-mock', 'object': 'chat.completion', 'created': 1, 'model': body['model'],
                      'choices': [{'index': 0, 'message': message, 'finish_reason': finish}],
                      'usage': {'prompt_tokens': 1, 'completion_tokens': 1, 'total_tokens': 2}}
        else:
            self.send_error(404)
            return
        encoded = json.dumps(result).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


class YandexGatewayTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).parent
        cls.temp = tempfile.TemporaryDirectory()
        cls.backend = ThreadingHTTPServer(('127.0.0.1', 0), FakeYandex)
        cls.backend.daemon_threads = True
        cls.backend.calls = []
        threading.Thread(target=cls.backend.serve_forever, daemon=True).start()
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        cls.base = f'http://127.0.0.1:{port}'
        config = yaml.safe_load((cls.root / 'litellm_config.yaml').read_text())
        config['model_list'] = [m for m in config['model_list'] if m['model_name'].startswith('yandex/')]
        config['general_settings'].pop('database_url', None)
        config['litellm_settings']['check_provider_endpoint'] = False
        path = Path(cls.temp.name) / 'config.yaml'
        path.write_text(yaml.safe_dump(config))
        # LiteLLM resolves file-backed hooks relative to the config location.
        for name in ('cloudru_compat.py', 'yandex_compat.py'):
            shutil.copy2(cls.root / name, Path(cls.temp.name) / name)
        env = dict(os.environ, LITELLM_MASTER_KEY='sk-offline-gateway-test', YANDEX_API_KEY='offline-provider-key',
                   YANDEX_API_BASE=f'http://127.0.0.1:{cls.backend.server_port}/v1', YANDEX_FOLDER_ID='test-folder',
                   YANDEX_CHAT_MODEL='openai/gpt://test-folder/aliceai-llm-flash/latest',
                   YANDEX_LITE_MODEL='openai/gpt://test-folder/yandexgpt-lite/latest',
                   YANDEX_EMBEDDING_MODEL='openai/emb://test-folder/text-embeddings-v2-doc/latest',
                   YANDEX_QUERY_EMBEDDING_MODEL='openai/emb://test-folder/text-embeddings-v2-query/latest',
                   PYTHONPATH=str(cls.root), LITELLM_LOCAL_MODEL_COST_MAP='True', PYTHONDONTWRITEBYTECODE='1')
        cls.log = open(Path(cls.temp.name) / 'gateway.log', 'w+')
        cls.process = subprocess.Popen([shutil.which('litellm'), '--config', str(path),
                                       '--host', '127.0.0.1', '--port', str(port)],
                                      cwd=cls.root, env=env, stdout=cls.log, stderr=subprocess.STDOUT)
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen(cls.base + '/health/liveliness', timeout=1):
                    return
            except Exception:
                if cls.process.poll() is not None:
                    break
                time.sleep(0.2)
        cls.process.terminate()
        cls.process.wait(timeout=10)
        cls.log.seek(0)
        output = cls.log.read()[-5000:]
        cls.backend.shutdown()
        cls.log.close()
        cls.temp.cleanup()
        raise AssertionError('Offline gateway did not start: ' + output)

    @classmethod
    def tearDownClass(cls):
        cls.process.terminate()
        try:
            cls.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            cls.process.kill()
            cls.process.wait()
        cls.backend.shutdown()
        cls.backend.server_close()
        cls.log.close()
        cls.temp.cleanup()

    def request(self, path, payload):
        self.backend.calls.clear()
        req = urllib.request.Request(self.base + path, data=json.dumps(payload).encode(),
                                     headers={'Authorization': 'Bearer sk-offline-gateway-test',
                                              'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=20) as response:
            raw = response.read().decode()
        self.assertEqual(len(self.backend.calls), 1, 'Exactly one upstream request is permitted')
        call = self.backend.calls[0]
        self.assertEqual(call['authorization'], 'Bearer offline-provider-key')
        self.assertEqual(call['project'], 'test-folder')
        self.assertNotIn('client_metadata', call['body'])
        return raw, call

    def test_chat_aliases_and_model_uri(self):
        for alias, suffix in [('yandex/chat', 'aliceai-llm-flash'), ('yandex/lite', 'yandexgpt-lite')]:
            raw, call = self.request('/v1/chat/completions', {'model': alias,
                'messages': [{'role': 'user', 'content': 'synthetic'}], 'max_tokens': 16})
            self.assertEqual(json.loads(raw)['choices'][0]['message']['content'], 'MOCK_OK')
            self.assertEqual(call['body']['model'], f'gpt://test-folder/{suffix}/latest')

    def test_responses_bridge_and_metadata(self):
        raw, call = self.request('/v1/responses', {'model': 'yandex/chat', 'input': 'synthetic',
            'max_output_tokens': 16, 'client_metadata': {'source': 'offline-test'}})
        body = json.loads(raw)
        self.assertEqual(body['status'], 'completed')
        self.assertEqual(body['output'][0]['content'][0]['text'], 'MOCK_OK')
        self.assertEqual(call['path'], '/v1/chat/completions')

    def test_responses_sse_completes_with_text(self):
        raw, call = self.request('/v1/responses', {'model': 'yandex/chat', 'input': 'synthetic',
            'stream': True, 'max_output_tokens': 16})
        events = [json.loads(line[6:]) for line in raw.splitlines() if line.startswith('data: {')]
        completed = next(e for e in events if e['type'] == 'response.completed')
        self.assertEqual(completed['response']['status'], 'completed')
        self.assertEqual(completed['response']['output'][0]['content'][0]['text'], 'MOCK_OK')
        self.assertTrue(call['body']['stream'])

    def test_responses_function_call(self):
        raw, call = self.request('/v1/responses', {'model': 'yandex/chat', 'input': 'synthetic',
            'tools': [{'type': 'function', 'name': 'probe', 'parameters': {'type': 'object',
                       'properties': {'value': {'type': 'string'}}, 'required': ['value']}}],
            'tool_choice': 'required', 'max_output_tokens': 64})
        tool = next(o for o in json.loads(raw)['output'] if o['type'] == 'function_call')
        self.assertEqual(tool['name'], 'probe')
        self.assertEqual(json.loads(tool['arguments']), {'value': 'OK'})
        self.assertEqual(call['body']['tools'][0]['function']['name'], 'probe')

    def test_embeddings_use_separate_doc_and_query_uris(self):
        for alias, suffix in [('yandex/embeddings', 'doc'), ('yandex/embeddings-query', 'query')]:
            raw, call = self.request('/v1/embeddings', {'model': alias, 'input': ['synthetic']})
            self.assertEqual(json.loads(raw)['data'][0]['embedding'], [0.25, 0.5, 0.75])
            self.assertEqual(call['path'], '/v1/embeddings')
            self.assertEqual(call['body']['model'], f'emb://test-folder/text-embeddings-v2-{suffix}/latest')


if __name__ == '__main__':
    unittest.main()
