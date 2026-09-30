# Состояние моделей на 30 сентября 2026 года

Получены полные списки `/v1/models`: **81 NVIDIA ID**, **95 Cloud.ru ID**. Снимки и обезличенные результаты лежат в [catalogs/](catalogs/). Каталог не означает доступность inference или поддержку всех API.

В таблицах ниже приведены сохранённые проверки upstream, а не оценка качества моделей. Текстовый запрос ограничивался 128 выходными токенами, запрос tools — 1024. Таймаут chat составлял 40 секунд, tools — 50 секунд. Время ответа зависит от нагрузки.

## NVIDIA NIM

Прямой API NVIDIA с проверенного хоста возвращает HTTP 451. Проверки выполнены с тем же ключом через временный SSH-туннель с разрешённого сервера. По умолчанию проект использует публичный API; сетевую доступность нужно обеспечить отдельно.

| NVIDIA ID | Chat | Tools |
| --- | --- | --- |
| `deepseek-ai/deepseek-v4.1-flash` | таймаут 40 с | не запускалось |
| `google/gemma-4-31b-it` | таймаут 40 с | не запускалось |
| `moonshotai/kimi-k2.6` | HTTP 404 | не запускалось |
| `moonshotai/kimi-k3` | таймаут 40 с | не запускалось |
| `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` | успешно, 1.17 с | HTTP 503 |
| `nvidia/nemotron-3-super-120b-a12b` | успешно, 1.05 с | HTTP 500 |
| `nvidia/nemotron-3-ultra-550b-a55b` | успешно, 3.70 с | успешно, 4.82 с |
| `nvidia/nemotron-3.5-lightning-30b-a3b` | успешно, 5.87 с | успешно, 1.65 с |
| `nvidia/nemotron-4-340b-instruct` | HTTP 404 | не запускалось |
| `nvidia/nemotron-nano-3-30b-a3b` | HTTP 404 | не запускалось |
| `openai/gpt-oss-20b` | успешно, 1.58 с | успешно, 0.92 с |
| `poolside/laguna-xs-2.1` | таймаут 40 с | не запускалось |
| `writer/palmyra-creative-122b` | HTTP 404 | не запускалось |
| `z-ai/glm-5.3` | таймаут 40 с | не запускалось |
| `z-ai/glm-5.3-flash` | успешно, 33.78 с | успешно, 49.79 с |

В `nim/agent` и `nim/code` включены `openai/gpt-oss-20b`, `nvidia/nemotron-3.5-lightning-30b-a3b` и `nvidia/nemotron-3-ultra-550b-a55b`. Super сохранён для обычного chat, но исключён из агентных алиасов после ошибки tools. `z-ai/glm-5.3-flash` опубликован точным маршрутом: он прошёл проверки, но отвечал медленно.

### Удалённые NVIDIA маршруты

Следующие 10 ID отсутствуют в текущем каталоге и удалены из конфигурации:

- `deepseek-ai/deepseek-v4-flash`
- `meta/llama-3.1-8b-instruct`
- `minimaxai/minimax-m3`
- `mistralai/mistral-nemotron`
- `nvidia/nemoretriever-parse`
- `nvidia/nemotron-3-nano-30b-a3b`
- `nvidia/nemotron-nano-12b-v2-vl`
- `nvidia/nvidia-nemotron-nano-9b-v2`
- `openai/gpt-oss-120b`
- `stepfun-ai/step-3.7-flash`

### Изображения, OCR и embeddings

| NVIDIA ID | Проверка | Результат |
| --- | --- | --- |
| `meta/llama-3.2-11b-vision-instruct` | image | успешно, 0.81 с |
| `nvidia/nemotron-parse` | structured | успешно, 1.91 с |
| `nvidia/nemotron-parse-2.0` | structured | HTTP 500 |
| `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` | video | HTTP 503 |
| `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` | audio | HTTP 503 |
| `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` | image | успешно, 7.01 с |

Nemotron Parse получает только изображение без текстового блока; endpoint возвращает структурированный OCR. Parse 2.0 не включён после HTTP 500. Видео и аудио Omni вернули HTTP 503; маршрут сохранён для совместимости, успешность этих режимов сейчас не подтверждена. Генерация изображений/видео и специализированные ASR/TTS маршруты не добавлены.

| Провайдер | Embeddings ID | Результат | Размерность |
| --- | --- | --- | ---: |
| nvidia | `nvidia/nemotron-3-embed-1b` | успешно, 0.44 с | 2048 |
| cloudru | `BAAI/bge-m3` | успешно, 0.41 с | 1024 |

## Cloud.ru

Используются **только ранее полученные результаты**. После согласованного ограничения дополнительные запросы к Cloud.ru не выполняются. Было 13 chat-попыток, 11 tools-запросов и один embeddings-запрос. Таймаут клиента не гарантирует отсутствие тарификации на стороне провайдера.

| Cloud.ru ID | Chat | Tools |
| --- | --- | --- |
| `MiniMaxAI/MiniMax-M3` | таймаут 40 с | не запускалось |
| `Qwen/Qwen3-Coder-Next` | успешно, 0.49 с | успешно, 0.58 с |
| `Qwen/Qwen3.6-35B-A3B` | HTTP 200, только reasoning (лимит токенов) | успешно, 1.10 с |
| `ai-sage/GigaChat3-10B-A1.8B` | успешно, 0.46 с | успешно, 0.32 с |
| `ai-sage/GigaChat3.5-432B-A28B` | успешно, 1.05 с | успешно, 1.33 с |
| `deepseek-ai/DeepSeek-V4-Flash` | успешно, 1.62 с | успешно, 1.83 с |
| `deepseek-ai/DeepSeek-V4-Pro` | успешно, 1.21 с | успешно, 2.52 с |
| `deepseek-ai/DeepSeek-V4.1-Flash` | успешно, 1.15 с | успешно, 1.13 с |
| `moonshotai/Kimi-K2.6` | успешно, 2.48 с | успешно, 3.86 с |
| `xiaomi/mimo-v2.5` | успешно, 6.99 с | успешно, 6.01 с |
| `zai-org/GLM-4.7` | таймаут 40 с | не запускалось |
| `zai-org/GLM-5.1` | успешно, 16.48 с | успешно, 5.08 с |
| `zai-org/GLM-5.2` | успешно, 5.93 с | успешно, 5.79 с |

В YAML добавлены 11 ответивших текстовых моделей и MiniMax M3 для совместимости старых клиентов. GLM 4.7 после таймаута не добавлен. Для Qwen3.6 успешный transport не означает завершённый текстовый ответ: при 128 токенах он вернул только рассуждение.

Новые точные маршруты имеют префикс `cloudru/`, например `cloudru/zai-org/GLM-5.2`. Старые ID без префикса сохранены для шести моделей: GigaChat3.5, GigaChat3, GLM-5.1, DeepSeek-V4-Pro, MiniMax-M3, Kimi-K2.6. Они всегда используют Cloud.ru. Облачные ключи берутся только из окружения; контекстные лимиты и capability-флаги взяты из каталога Cloud.ru, а не из ключей аккаунта.

Cloud.ru отсутствует в автоматических NVIDIA-алиасах и fallback-списках. Повторные inference-запросы шлюза отключены. Responses history hook проверяется офлайн с реальным преобразователем LiteLLM 1.93.0; новые живые проверки Responses/SSE Cloud.ru не выполнялись.

## Локальные модели

На хосте обнаружены Ollama `gemma4:12b` и `qwen3.5:9b-q8_0`. Прежнее `gemma4:latest` отсутствует; пример окружения исправлен на `ollama_chat/gemma4:12b`.

LM Studio на порту 1234 не работает; текущие Chat/Responses/tools для неё не проверены. Инструкции по Granite в LOCAL_MODELS_RU.md относятся к конфигурации, проверенной в июле, и не подтверждают наличие модели сейчас. Модель Qwen3.5 обнаружена в каталоге Ollama, но её inference отдельно не запускался.

## Проверка собранного шлюза

Изолированный контейнер LiteLLM 1.93.0 запущен с новым конфигом на временном loopback-порту, без PostgreSQL и с отключённым Cloud.ru upstream. Рабочая база и контейнер не использовались. Результаты: [catalogs/gateway-checks.json](catalogs/gateway-checks.json).

- Конфигурация всех маршрутов, включая Cloud.ru, успешно загружена; каталог Ollama обнаруживает обе установленные модели.
- NVIDIA `openai/gpt-oss-20b`: Responses API с `client_metadata`, SSE с завершённым текстом и Responses tools — успешно.
- NVIDIA `nim/embeddings`: 2048 измерений — успешно.
- Ollama `local/ollama` → `gemma4:12b`: Chat, Responses и tools — успешно.
- Регрессии Cloud.ru Responses history выполнены в Docker без сети; live inference Cloud.ru при этой проверке не запускался.

Скрипты проверяют непустой конечный текст; один только reasoning не считается успешным текстовым ответом. Статическая проверка сверяет NVIDIA/Cloud.ru IDs со снимками каталога, исключает embedding-модели из Chat и проверяет tools для агентных алиасов. GitHub Actions выполняет только офлайн-проверки.

## Яндекс AI Studio

30 сентября 2026 года endpoint `https://ai.api.cloud.yandex.net/v1/models` проверен чтением каталога с предоставленным API-ключом: HTTP 200, 27 записей, Bearer-авторизация работает. Генерация и embeddings при обнаружении не вызывались. Снимок с заменой ID каталога на `{folder_id}`: [catalogs/yandex-catalog.json](catalogs/yandex-catalog.json).

Добавлены явные маршруты `yandex/chat`, `yandex/lite`, `yandex/embeddings`, `yandex/embeddings-query`. Начальные модели: AliceAI LLM Flash, YandexGPT Lite, Text Embeddings v2 Doc и Query. Эти маршруты не входят в NVIDIA-алиасы; автоматические повторы отключены. Для AliceAI LLM Flash успешно проверены Chat, Responses, Responses SSE и tools через отдельный шлюз LiteLLM 1.93.0. Выполнены ровно четыре согласованных обращения к upstream, до 128 выходных токенов на запрос. Результаты: [catalogs/yandex-live-checks.json](catalogs/yandex-live-checks.json). YandexGPT Lite, остальные текстовые модели и embeddings живыми запросами не проверялись.

Дополнительно подключены десять обычных текстовых `latest`-моделей из того же снимка: AliceAI LLM, YandexGPT 5 Lite/Pro/5.1 и YandexGPT, DeepSeek V4/V4.1 Flash, GPT-OSS 20B/120B и Qwen3.6-35B-A3B. В меню Codex теперь 12 маршрутов. Новых upstream inference-запросов при расширении не выполнялось. Эти модели не считаются проверенными по наличию в меню.

Все 38 офлайн-тестов прошли. Регрессии на локальной имитации OpenAI-совместимого API проверяют: передача Bearer-ключа, OpenAI-Project, URI, мост Responses → Chat, SSE, tools, отдельные embeddings-маршруты и чтение всех моделей меню без генерации. Валидатор также проверяет приватные маршруты Яндекса/Cloud.ru через отдельные переменные окружения, сохранение границ провайдеров и запрет записи частного URI прямо в публичный YAML. Это проверяет наш шлюз, но не заменяет проверки доступности функций у провайдера. Подробности: [YANDEX_RU.md](YANDEX_RU.md).
