"""Offline validation of catalogue membership and safe gateway routing."""
import json
import pathlib
import re
import yaml


def validate(config, catalogs, checks):
    deployments = config['model_list']
    seen = set()
    tool_ok = {c['model'] for c in checks if c['provider'] == 'nvidia' and c['tools'] and c['tools']['ok']}
    for entry in deployments:
        name = entry['model_name']
        params = entry['litellm_params']
        model = params['model']
        assert (name, model) not in seen, f'Duplicate deployment: {name}, {model}'
        seen.add((name, model))
        for key in ('api_key', 'api_base'):
            if key in params:
                assert params[key].startswith('os.environ/'), f'{name}: {key} must use environment'
        if model.startswith('nvidia_nim/'):
            upstream = model.removeprefix('nvidia_nim/')
            assert upstream in catalogs['nvidia'], f'Retired NVIDIA ID: {upstream}'
            if name in ('nim/agent', 'nim/code'):
                assert upstream in tool_ok, f'Unverified tools in {name}: {upstream}'
        elif name.startswith('cloudru/') or params.get('api_key', '').startswith('os.environ/CLOUDRU_'):
            assert not name.startswith('nim/'), f'Cloud.ru in automatic NVIDIA route: {name}'
            assert params.get('api_key', '').startswith('os.environ/CLOUDRU_'), f'Wrong Cloud.ru credentials: {name}'
            assert params.get('api_base', '').startswith('os.environ/CLOUDRU_'), f'Wrong Cloud.ru endpoint: {name}'
            if model.startswith('os.environ/'):
                assert name.startswith('cloudru/'), f'Custom Cloud.ru route needs provider prefix: {name}'
                assert re.fullmatch(r'os\.environ/CLOUDRU_[A-Z0-9_]+_MODEL', model), f'Custom Cloud.ru model must use provider environment: {name}'
                assert entry['model_info']['mode'] in ('chat', 'embedding'), f'Wrong custom Cloud.ru mode: {name}'
                assert params.get('max_retries') == 0, f'Custom Cloud.ru SDK retries enabled: {name}'
            else:
                upstream = model.removeprefix('openai/')
                assert upstream in catalogs['cloudru'], f'Unknown Cloud.ru ID: {upstream}'
            if entry['model_info']['mode'] == 'chat':
                assert params.get('use_chat_completions_api') is True, f'Missing Responses bridge: {name}'
        elif name.startswith('yandex/') or params.get('api_key', '').startswith('os.environ/YANDEX_'):
            assert name.startswith('yandex/'), f'Yandex in another provider route: {name}'
            assert params.get('api_key', '').startswith('os.environ/YANDEX_'), f'Wrong Yandex credentials: {name}'
            expected = {
                'yandex/chat': ('YANDEX_CHAT_MODEL', 'chat'),
                'yandex/lite': ('YANDEX_LITE_MODEL', 'chat'),
                'yandex/embeddings': ('YANDEX_EMBEDDING_MODEL', 'embedding'),
                'yandex/embeddings-query': ('YANDEX_QUERY_EMBEDDING_MODEL', 'embedding'),
            }
            if name in expected:
                variable, mode = expected[name]
                assert model == 'os.environ/' + variable, f'Yandex URI must use environment: {name}'
                assert entry['model_info']['mode'] == mode, f'Wrong Yandex endpoint mode: {name}'
            else:
                assert re.fullmatch(r'os\.environ/YANDEX_[A-Z0-9_]+_MODEL', model), f'Yandex URI must use environment: {name}'
                mode = entry['model_info']['mode']
                assert mode in ('chat', 'embedding'), f'Wrong Yandex endpoint mode: {name}'
            assert params.get('api_base', '').startswith('os.environ/YANDEX_'), f'Wrong Yandex endpoint: {name}'
            assert params['max_retries'] == 0, f'Yandex SDK retries enabled: {name}'
            if mode == 'chat':
                assert params.get('use_chat_completions_api') is True, f'Missing Yandex Responses bridge: {name}'
        if 'embed' in model.lower() or model.endswith('BAAI/bge-m3'):
            assert entry['model_info']['mode'] == 'embedding', f'Embedding model treated as chat: {name}'
    names = {e['model_name'] for e in deployments}
    assert {'local/ollama', 'local/lmstudio', 'ollama/*', 'lmstudio/*', 'nim/embeddings'} <= names
    assert config['router_settings']['num_retries'] == 0, 'Automatic inference retries must be disabled'
    assert config['router_settings']['default_litellm_params']['max_retries'] == 0, 'SDK retries must be disabled'
    assert config['litellm_settings']['DEFAULT_MAX_RETRIES'] == 0, 'Embedding SDK retry default must be zero'
    assert not config['router_settings'].get('fallbacks'), 'Automatic cross-provider fallbacks are disabled'
    assert not config['router_settings'].get('default_fallbacks'), 'Default provider fallbacks are disabled'
    assert config['litellm_settings']['callbacks'] == [
        'cloudru_compat.proxy_handler_instance', 'yandex_compat.proxy_handler_instance']
    assert config['litellm_settings']['check_provider_endpoint'] is True


if __name__ == '__main__':
    root = pathlib.Path(__file__).parent
    catalogs = {name: set(json.loads((root / f'catalogs/{name}-catalog.json').read_text())['ids'])
                for name in ('nvidia', 'cloudru')}
    checks = json.loads((root / 'catalogs/candidate-checks.json').read_text())
    config = yaml.safe_load((root / 'litellm_config.yaml').read_text())
    validate(config, catalogs, checks)
    compose = yaml.safe_load((root / 'docker-compose.yml').read_text())
    service = compose['services']['litellm']
    assert './cloudru_compat.py:/app/cloudru_compat.py:ro' in service['volumes']
    assert './yandex_compat.py:/app/yandex_compat.py:ro' in service['volumes']
    assert 'sha256:72360d8bd5602faa49be5098a8ac3dd069d9fb74503d6bd014242d96dc753e43' in service['image']
    for param in ('CLOUDRU_API_KEY', 'CLOUDRU_API_BASE', 'NVIDIA_NIM_API_BASE',
                  'YANDEX_API_KEY', 'YANDEX_API_BASE', 'YANDEX_FOLDER_ID', 'YANDEX_CHAT_MODEL',
                  'YANDEX_LITE_MODEL', 'YANDEX_EMBEDDING_MODEL', 'YANDEX_QUERY_EMBEDDING_MODEL'):
        assert param in service['environment'], f'Missing Compose environment: {param}'
    for deployment in config['model_list']:
        for param in ('model', 'api_key', 'api_base'):
            value = deployment['litellm_params'].get(param, '')
            if value.startswith(('os.environ/YANDEX_', 'os.environ/CLOUDRU_')):
                variable = value.removeprefix('os.environ/')
                assert variable in service['environment'], f'Missing Compose environment: {variable}'
    print(f'YAML, catalogue membership and routing: OK ({len(config["model_list"])} deployments)')
