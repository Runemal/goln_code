"""Compatibility for Codex histories sent through Cloud.ru's Responses bridge.

Responses represents one assistant turn as separate text, reasoning and tool
call items. Codex may persist text AFTER the calls. LiteLLM 1.93.0 only merges
calls into the preceding assistant message, so trailing text breaks the
adjacency required by the upstream tool parser. Normalize each contiguous
assistant turn to text/reasoning followed by calls. Preserve all nonempty
content, call order, IDs, arguments and results, without crossing tool outputs
or user/developer/system messages. No calls are synthesized.
"""
from litellm.integrations.custom_logger import CustomLogger

CLOUDRU_MODELS = {
    'ai-sage/GigaChat3.5-432B-A28B', 'ai-sage/GigaChat3-10B-A1.8B',
    'zai-org/GLM-5.1', 'deepseek-ai/DeepSeek-V4-Pro',
    'MiniMaxAI/MiniMax-M3', 'moonshotai/Kimi-K2.6',
}


def normalize_codex_input(items):
    result = []
    turn = []

    def flush():
        calls = [item for item in turn if item.get('type') in ('function_call', 'custom_tool_call')]
        if not calls:
            result.extend(turn)
            turn.clear()
            return
        for item in turn:
            if item.get('type') in ('function_call', 'custom_tool_call'):
                continue
            content = item.get('content')
            empty = content == '' or (isinstance(content, list) and all(
                isinstance(block, dict)
                and block.get('type') in ('input_text', 'output_text', 'text')
                and block.get('text') == ''
                for block in content
            ))
            if item.get('role') == 'assistant' and empty and not item.get('tool_calls'):
                continue
            result.append(item)
        result.extend(calls)
        turn.clear()

    for item in items:
        if isinstance(item, dict) and (
            item.get('type') in ('function_call', 'custom_tool_call', 'reasoning')
            or (item.get('type', 'message') == 'message' and item.get('role') == 'assistant')
        ):
            turn.append(item)
        else:
            flush()
            result.append(item)
    flush()
    return result


class CloudRuCodexCompatibility(CustomLogger):
    async def async_pre_call_hook(self, user_api_key_dict, cache, data, call_type):
        if (data.get('model') in CLOUDRU_MODELS or str(data.get('model', '')).startswith('cloudru/')) and isinstance(data.get('input'), list):
            normalized = normalize_codex_input(data['input'])
            if normalized != data['input']:
                return {**data, 'input': normalized}
        return data


proxy_handler_instance = CloudRuCodexCompatibility()
