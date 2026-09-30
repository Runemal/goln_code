"""Regression checks for catalogue and cost-sensitive routing invariants."""
import copy
import json
from pathlib import Path
import unittest
import yaml
from validate_config import validate


class RoutingTest(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).parent
        self.config = yaml.safe_load((root / 'litellm_config.yaml').read_text())
        self.catalogs = {name: set(json.loads((root / f'catalogs/{name}-catalog.json').read_text())['ids'])
                         for name in ('nvidia', 'cloudru')}
        self.checks = json.loads((root / 'catalogs/candidate-checks.json').read_text())

    def test_current_config_passes(self):
        validate(self.config, self.catalogs, self.checks)

    def test_paid_cloudru_model_cannot_enter_nvidia_alias(self):
        cloud = next(m for m in self.config['model_list'] if m['model_name'].startswith('cloudru/'))
        cloud['model_name'] = 'nim/agent'
        with self.assertRaisesRegex(AssertionError, 'Cloud.ru in automatic NVIDIA route'):
            validate(self.config, self.catalogs, self.checks)

    def test_yandex_model_cannot_enter_another_provider_alias(self):
        route = next(m for m in self.config['model_list'] if m['model_name'] == 'yandex/chat')
        route['model_name'] = 'nim/chat'
        with self.assertRaisesRegex(AssertionError, 'Yandex in another provider route'):
            validate(self.config, self.catalogs, self.checks)

    def test_yandex_embeddings_cannot_use_chat_mode(self):
        route = next(m for m in self.config['model_list'] if m['model_name'] == 'yandex/embeddings')
        route['model_info']['mode'] = 'chat'
        with self.assertRaisesRegex(AssertionError, 'Wrong Yandex endpoint mode'):
            validate(self.config, self.catalogs, self.checks)

    def test_private_yandex_deployment_can_use_its_own_credentials_and_endpoint(self):
        route = copy.deepcopy(next(m for m in self.config['model_list'] if m['model_name'] == 'yandex/chat'))
        route['model_name'] = 'yandex/my-deployment'
        route['litellm_params'].update(model='os.environ/YANDEX_MY_MODEL',
            api_key='os.environ/YANDEX_CUSTOM_API_KEY', api_base='os.environ/YANDEX_CUSTOM_API_BASE')
        self.config['model_list'].append(route)
        validate(self.config, self.catalogs, self.checks)

    def test_private_cloudru_deployment_can_use_an_id_outside_public_catalog(self):
        route = copy.deepcopy(next(m for m in self.config['model_list'] if m['model_name'].startswith('cloudru/')))
        route['model_name'] = 'cloudru/my-deployment'
        route['litellm_params'].update(model='os.environ/CLOUDRU_MY_MODEL',
            api_key='os.environ/CLOUDRU_CUSTOM_API_KEY', api_base='os.environ/CLOUDRU_CUSTOM_API_BASE', max_retries=0)
        self.config['model_list'].append(route)
        validate(self.config, self.catalogs, self.checks)

    def test_private_yandex_credentials_cannot_enter_nvidia_route(self):
        route = next(m for m in self.config['model_list'] if m['model_name'] == 'yandex/chat')
        route['model_name'] = 'nim/chat'
        route['litellm_params']['api_key'] = 'os.environ/YANDEX_CUSTOM_API_KEY'
        with self.assertRaisesRegex(AssertionError, 'Yandex in another provider route'):
            validate(self.config, self.catalogs, self.checks)

    def test_private_yandex_uri_cannot_be_embedded_in_public_yaml(self):
        route = next(m for m in self.config['model_list'] if m['model_name'] == 'yandex/chat')
        route['model_name'] = 'yandex/my-deployment'
        route['litellm_params']['model'] = 'openai/gpt://private-folder/my-model/latest'
        with self.assertRaisesRegex(AssertionError, 'Yandex URI must use environment'):
            validate(self.config, self.catalogs, self.checks)

    def test_unknown_literal_cloudru_id_still_requires_public_catalog_membership(self):
        route = next(m for m in self.config['model_list'] if m['model_name'].startswith('cloudru/'))
        route['litellm_params']['model'] = 'openai/not-in-public-catalog'
        with self.assertRaisesRegex(AssertionError, 'Unknown Cloud.ru ID'):
            validate(self.config, self.catalogs, self.checks)

    def test_untested_tools_cannot_enter_agent_pool(self):
        super_model = copy.deepcopy(next(m for m in self.config['model_list']
                                        if m['model_name'] == 'nvidia/nemotron-3-super-120b-a12b'))
        super_model['model_name'] = 'nim/agent'
        self.config['model_list'].append(super_model)
        with self.assertRaisesRegex(AssertionError, 'Unverified tools'):
            validate(self.config, self.catalogs, self.checks)

    def test_removed_id_cannot_return(self):
        self.config['model_list'][0]['litellm_params']['model'] = 'nvidia_nim/meta/llama-3.1-8b-instruct'
        with self.assertRaisesRegex(AssertionError, 'Retired NVIDIA ID'):
            validate(self.config, self.catalogs, self.checks)

    def test_embeddings_cannot_be_advertised_as_chat(self):
        embed = next(m for m in self.config['model_list'] if m['model_name'] == 'cloudru/BAAI/bge-m3')
        embed['model_info']['mode'] = 'chat'
        embed['litellm_params']['use_chat_completions_api'] = True
        with self.assertRaisesRegex(AssertionError, 'Embedding model treated as chat'):
            validate(self.config, self.catalogs, self.checks)


if __name__ == '__main__':
    unittest.main()
