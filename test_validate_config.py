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
