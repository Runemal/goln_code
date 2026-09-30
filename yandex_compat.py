"""Add the configured Yandex Cloud project to explicitly selected routes."""
import os
from litellm.integrations.custom_logger import CustomLogger


class YandexProjectHeaders(CustomLogger):
    async def async_pre_call_hook(self, user_api_key_dict, cache, data, call_type):
        if not str(data.get('model', '')).startswith('yandex/'):
            return data
        folder_id = os.environ.get('YANDEX_FOLDER_ID', '').strip()
        if not folder_id or folder_id.startswith(('replace-', 'not-configured')):
            raise ValueError('Set YANDEX_FOLDER_ID before calling a Yandex route')
        headers = dict(data.get('extra_headers') or {})
        headers['OpenAI-Project'] = folder_id
        return {**data, 'extra_headers': headers}


proxy_handler_instance = YandexProjectHeaders()
