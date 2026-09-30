import asyncio
import copy
import unittest

from cloudru_compat import normalize_codex_input, proxy_handler_instance
from litellm.responses.litellm_completion_transformation.transformation import LiteLLMCompletionResponsesConfig


def call(cid, kind='function_call'):
    return {'type': kind, 'name': 'list_mcp_resources', 'call_id': cid, 'arguments': '{}'}


def output(cid):
    return {'type': 'function_call_output', 'call_id': cid, 'output': '{"resources":[]}'}


EMPTY = {'type': 'message', 'role': 'assistant', 'content': [{'type': 'output_text', 'text': ''}]}


class CompatibilityTest(unittest.TestCase):
    def test_codex_mcp_history_keeps_call_adjacent_to_result(self):
        items = [call('a'), copy.deepcopy(EMPTY), output('a')]
        before = copy.deepcopy(items)
        fixed = normalize_codex_input(items)
        converted = LiteLLMCompletionResponsesConfig._transform_response_input_param_to_chat_completion_message(fixed)
        self.assertEqual([m['role'] for m in converted], ['assistant', 'tool'])
        self.assertEqual(converted[0]['tool_calls'][0]['id'], converted[1]['tool_call_id'])
        self.assertEqual(items, before)

    def test_parallel_tools_preserve_every_call_and_output(self):
        items = [call('a'), EMPTY, call('b'), EMPTY, output('a'), output('b')]
        converted = LiteLLMCompletionResponsesConfig._transform_response_input_param_to_chat_completion_message(normalize_codex_input(items))
        self.assertEqual([m['role'] for m in converted], ['assistant', 'tool', 'tool'])
        self.assertEqual([c['id'] for c in converted[0]['tool_calls']], ['a', 'b'])
        self.assertEqual([m['tool_call_id'] for m in converted[1:]], ['a', 'b'])

    def test_real_commentary_and_multimodal_content_are_preserved(self):
        for content in [[{'type': 'output_text', 'text': 'Checking resources'}],
                        [{'type': 'refusal', 'refusal': ''}],
                        [{'type': 'input_image', 'image_url': 'demo'}]]:
            message = {'type': 'message', 'role': 'assistant', 'content': content}
            items = [call('a'), message, output('a')]
            self.assertEqual(normalize_codex_input(items), [message, items[0], items[2]])

    def test_nonempty_commentary_after_parallel_resource_reads(self):
        first, second = call('a'), call('b')
        first.update(name='read_mcp_resource', arguments='{"uri":"demo://catalog","server":"regression"}')
        second.update(name='read_mcp_resource', arguments='{"uri":"demo://guide","server":"regression"}')
        commentary = {'type': 'message', 'role': 'assistant', 'id': 'msg_commentary',
                      'content': [{'type': 'output_text', 'text': 'Сейчас гляну каталог и гайд.'}]}
        items = [first, second, commentary, output('b'), output('a')]
        original = copy.deepcopy(items)
        fixed = normalize_codex_input(items)
        self.assertEqual(fixed, [commentary, first, second, items[3], items[4]])
        converted = LiteLLMCompletionResponsesConfig._transform_response_input_param_to_chat_completion_message(fixed)
        self.assertEqual([m['role'] for m in converted], ['assistant', 'tool', 'tool'])
        self.assertEqual([c['id'] for c in converted[0]['tool_calls']], ['a', 'b'])
        self.assertEqual([c['function']['arguments'] for c in converted[0]['tool_calls']], [first['arguments'], second['arguments']])
        self.assertIn('Сейчас гляну каталог и гайд.', str(converted[0]['content']))
        self.assertEqual([m['tool_call_id'] for m in converted[1:]], ['b', 'a'])
        self.assertEqual(items, original)
        self.assertEqual(normalize_codex_input(fixed), fixed)

    def test_hook_applies_reordering_even_when_length_is_unchanged(self):
        text = {'role': 'assistant', 'content': 'Reading resources'}
        data = {'model': 'MiniMaxAI/MiniMax-M3', 'input': [call('a'), text, output('a')]}
        fixed = asyncio.run(proxy_handler_instance.async_pre_call_hook(None, None, data, 'aresponses'))
        self.assertEqual(fixed['input'], [text, data['input'][0], data['input'][2]])

    def test_does_not_move_text_across_user_or_tool_results(self):
        a, b = call('a'), call('b')
        t1 = {'role': 'assistant', 'content': 'First'}
        t2 = {'role': 'assistant', 'content': 'Second'}
        user = {'role': 'user', 'content': 'Next turn'}
        items = [a, t1, output('a'), user, b, t2, output('b')]
        self.assertEqual(normalize_codex_input(items), [t1, a, items[2], user, t2, b, items[6]])

    def test_reasoning_and_custom_tool_inputs_are_preserved(self):
        custom = {'type': 'custom_tool_call', 'call_id': 'c', 'name': 'apply_patch', 'input': 'literal input'}
        reasoning = {'type': 'reasoning', 'id': 'rs_1', 'summary': [{'type': 'summary_text', 'text': 'Plan'}]}
        text = {'role': 'assistant', 'content': 'Calling'}
        result = {'type': 'custom_tool_call_output', 'call_id': 'c', 'output': 'done'}
        self.assertEqual(normalize_codex_input([custom, reasoning, text, result]), [reasoning, text, custom, result])

    def test_empty_messages_outside_tool_round_trip_are_preserved(self):
        for items in [[EMPTY], [call('a'), output('a'), EMPTY],
                      [call('a'), {'role': 'user', 'content': 'New turn'}, EMPTY]]:
            self.assertEqual(normalize_codex_input(items), items)

    def test_other_providers_and_chat_requests_are_untouched(self):
        for data in [{'model': 'nim/agent', 'input': [call('a'), EMPTY, output('a')]},
                     {'model': 'MiniMaxAI/MiniMax-M3', 'messages': [{'role': 'assistant', 'content': ''}]}]:
            self.assertIs(asyncio.run(proxy_handler_instance.async_pre_call_hook(None, None, data, 'aresponses')), data)

    def test_namespaced_cloudru_route_normalizes_without_mutating_history(self):
        text = {'role': 'assistant', 'content': 'Reading resources'}
        data = {'model': 'cloudru/Qwen/Qwen3-Coder-Next', 'input': [call('a'), text, output('a')]}
        before = copy.deepcopy(data)
        fixed = asyncio.run(proxy_handler_instance.async_pre_call_hook(None, None, data, 'aresponses'))
        self.assertEqual(fixed['input'], [text, data['input'][0], data['input'][2]])
        self.assertEqual(data, before)

    def test_namespaced_chat_requests_are_untouched(self):
        data = {'model': 'cloudru/Qwen/Qwen3-Coder-Next', 'messages': [EMPTY]}
        self.assertIs(asyncio.run(proxy_handler_instance.async_pre_call_hook(None, None, data, 'acompletion')), data)

    def test_cloudru_responses_hook_and_custom_calls(self):
        items = [call('a', 'custom_tool_call'), EMPTY,
                 {'type': 'custom_tool_call_output', 'call_id': 'a', 'output': 'done'}]
        data = {'model': 'MiniMaxAI/MiniMax-M3', 'input': items}
        result = asyncio.run(proxy_handler_instance.async_pre_call_hook(None, None, data, 'aresponses'))
        self.assertEqual(result['input'], [items[0], items[2]])
        self.assertEqual(len(data['input']), 3)


if __name__ == '__main__':
    unittest.main()
