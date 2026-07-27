# Состояние моделей NVIDIA NIM

Первичная проверка выполнена 25 июля 2026 года; текстовые маршруты и каталог повторно проверены 27 июля 2026 года для текущего NVIDIA API-аккаунта.

- Записей в `/v1/models`: **118**.
- Текстовые модели проверялись полным ответом `chat/completions` без streaming.
- Таймаут первичного отбора: 30 секунд.
- Вызов инструментов проверялся отдельным запросом с JSON Schema.
- Мультимодальные модели проверялись на синтетических PNG, MP4 и WAV.
- Доступность и загрузка NVIDIA меняются со временем.

## Проверенные локальные маршруты

Повторная проверка Ollama и LM Studio выполнена 27 июля 2026 года через активный контейнер LiteLLM и Codex CLI.

| Маршрут | Модель | Chat | Responses | Tools | Codex |
| --- | --- | --- | --- | --- | --- |
| `local/ollama` | `gemma4:latest` | успешно | успешно | успешно | успешно |
| `local/ollama` напрямую | `yandex/YandexGPT-5-Lite-8B-instruct-GGUF:latest` | успешно | — | — | — |
| `local/lmstudio` | `granite-4.0-h-tiny` | успешно | успешно | успешно | успешно |

Динамическое обнаружение LiteLLM 1.93.0 проверено отдельно: опубликованы 5 маршрутов `ollama/*` и 2 маршрута `lmstudio/*`. Точные маршруты `ollama/gemma4:latest` и `lmstudio/granite-4.0-h-tiny` прошли Chat, Responses и tools; `lmstudio/text-embedding-nomic-embed-text-v1.5` успешно прошёл `/v1/embeddings`. Проверка каталога не означает, что каждая найденная модель поддерживает все эти API.

LM Studio была проверена без API-аутентификации, с привязкой `0.0.0.0:1234` и контекстом `248064`. При этой конфигурации суммарное наблюдаемое использование RTX 3060 12 ГБ составляло около 7,7 ГБ. После аварийной перезагрузки JIT сначала загрузил модель с контекстом `8192`; явная команда `lms load ... --context-length 248064` вернула проверенную конфигурацию, после чего Chat, Responses, SSE и tools снова прошли.

При двух одновременно загруженных экземплярах LM Studio Ollama `gemma4` падала из-за нехватки GPU-ресурсов. После выгрузки моделей LM Studio прямой запрос, LiteLLM и Codex прошли успешно.

## Рекомендованные текстовые модели

| Идентификатор модели | Задержка chat | Вызов инструментов |
| --- | ---: | --- |
| `nvidia/nemotron-3-super-120b-a12b` | 0,62 с | успешно |
| `openai/gpt-oss-20b` | 0,57 с | успешно |
| `meta/llama-3.1-8b-instruct` | 0,53 с | не проверялось |

## Доступны, но чувствительны к загрузке

| Идентификатор модели | Наблюдение |
| --- | --- |
| `deepseek-ai/deepseek-v4-flash` | chat сработал за 4,48 с; последующая проверка tools получила 503 `ResourceExhausted` |
| `nvidia/nemotron-3-ultra-550b-a55b` | chat сработал за 0,76 с; последующая проверка tools получила 503 |
| `mistralai/mistral-nemotron` | 27 июля не ответила за 20 секунд; удалена из автоматических алиасов |
| `stepfun-ai/step-3.7-flash` | 27 июля не ответила за 20 секунд; удалена из автоматических алиасов |
| `minimaxai/minimax-m3` | 27 июля не ответила за 30 секунд; удалена из автоматических алиасов |
| `openai/gpt-oss-120b` | обычный chat прошёл, но tool/reasoning проверки зависали; оставлена только точным маршрутом |
| `meta/llama-3.3-70b-instruct` | ответ за 11,72 с |
| `poolside/laguna-xs-2.1` | ответ за 7,69 с |

Эти модели опубликованы как точные маршруты, но не входят в основные автоматические алиасы.

## Мультимодальные модели

| Модель или алиас | Проверка | Результат |
| --- | --- | --- |
| `meta/llama-3.2-11b-vision-instruct` | OCR изображения | точный текст, 0,74 с |
| `nvidia/nemotron-nano-12b-v2-vl` | OCR изображения | точный текст, 1,54 с |
| `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` | OCR изображения | точный текст, 0,93 с |
| `nim/omni` | анализ MP4 через LiteLLM | успешно, 2,74 с |
| `nim/omni` | анализ WAV через LiteLLM | успешно, 2,81 с |
| `nvidia/nemotron-parse` | структурированный OCR | корректный текст и bbox через `markdown_bbox` |
| `nvidia/nemoretriever-parse` | структурированный OCR | корректный текст и bbox через `markdown_bbox` |

Модели Nemotron Parse должны получать только изображение. Добавление текстовой части приводит к HTTP 400.

## Записи каталога, недоступные аккаунту

Отключены провайдером после первоначальной проверки:

- `qwen/qwen3-next-80b-a3b-instruct` — HTTP 410, завершение поддержки 27 июля 2026 года; удалена из маршрутов и алиасов.
- `meta/llama-4-maverick-17b-128e-instruct` — HTTP 410, завершение поддержки 27 июля 2026 года; удалена из маршрутов и алиасов.
- `mistralai/mistral-small-4-119b-2603` — HTTP 410, завершение поддержки 27 июля 2026 года; удалена из маршрутов и алиасов.
- `upstage/solar-10.7b-instruct` — HTTP 410, завершение поддержки 27 июля 2026 года; удалена из маршрутов и алиасов.
- `minimaxai/minimax-m2.7` — отсутствует в актуальном `/v1/models`; удалена из конфига.

Немедленный HTTP 404 или `model not found`:

- `01-ai/yi-large`
- `ai21labs/jamba-1.5-large-instruct`
- `google/gemma-3-4b-it`
- `microsoft/phi-3.5-moe-instruct`
- `mistralai/mistral-large`
- `moonshotai/kimi-k2.6`
- `nv-mistralai/mistral-nemo-12b-instruct`
- `qwen/qwen3.5-397b-a17b`
- `bigcode/starcoder2-15b`
- `deepseek-ai/deepseek-coder-6.7b-instruct`
- `ibm/granite-34b-code-instruct`
- `mistralai/codestral-22b-instruct-v0.1`
- `zyphra/zamba2-7b-instruct`
- `nvidia/cosmos-reason2-8b`

Не получен ответ за 30 секунд:

- `bytedance/seed-oss-36b-instruct`
- `deepseek-ai/deepseek-v4-pro`
- `google/gemma-4-31b-it`
- `mistralai/ministral-14b-instruct-2512`
- `mistralai/mistral-medium-3.5-128b`
- `nvidia/llama-3.1-nemotron-nano-8b-v1`
- `z-ai/glm-5.2`

Точные маршруты прежнего рабочего конфига сохранены для совместимости, даже если модель была нестабильна во время повторной проверки.

## Генерация изображений, видео и работа со звуком

В доступном OpenAI-совместимом каталоге отсутствуют text-to-image и text-to-video модели. `google/diffusiongemma-26b-a4b-it` — текстовая diffusion-LLM, а не генератор изображений.

Отдельных ASR и TTS моделей в `/v1/models` также нет. Аудио-вход доступен через `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`, но это мультимодальное понимание, а не специализированный speech-to-text или text-to-speech сервис.
