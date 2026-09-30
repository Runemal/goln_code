# Яндекс AI Studio через LiteLLM

Яндекс подключается обычным OpenAI-совместимым API на `https://ai.api.cloud.yandex.net/v1`. Отдельный SDK для работы шлюза не требуется. Проверка 30 сентября 2026 года с предоставленным API-ключом: `GET /models` вернул HTTP 200 и 27 записей; `Authorization: Bearer` принимается. Сам ключ и ID каталога в репозитории отсутствуют.

## Доступ и модели

В `.env` задайте `YANDEX_API_KEY` и `YANDEX_FOLDER_ID`. Модель передаётся полным URI, например `gpt://<folder_id>/aliceai-llm-flash/latest`; в параметре LiteLLM нужен префикс `openai/`.

```dotenv
YANDEX_API_BASE=https://ai.api.cloud.yandex.net/v1
YANDEX_API_KEY=replace-me
YANDEX_FOLDER_ID=replace-with-folder-id
YANDEX_CHAT_MODEL=openai/gpt://${YANDEX_FOLDER_ID}/aliceai-llm-flash/latest
YANDEX_LITE_MODEL=openai/gpt://${YANDEX_FOLDER_ID}/yandexgpt-lite/latest
YANDEX_EMBEDDING_MODEL=openai/emb://${YANDEX_FOLDER_ID}/text-embeddings-v2-doc/latest
YANDEX_QUERY_EMBEDDING_MODEL=openai/emb://${YANDEX_FOLDER_ID}/text-embeddings-v2-query/latest
```

Compose раскрывает `${YANDEX_FOLDER_ID}` из `.env`. При задании переменных напрямую через окружение передавайте уже полный URI, без литерала `${YANDEX_FOLDER_ID}`.

Если API-ключ хранится отдельно в `yandex.env`, перенесите значение в приватный `.env` с помощью локального редактора. Файл с одним сырым ключом не является shell-окружением, его нельзя выполнять через `source`. Установите права 600 на файлы с ключами. `*.env` исключены из Git; в `.env.example` находятся только заглушки.

Используйте существующий API-ключ сервисного аккаунта с доступом к нужному каталогу. Временный IAM-токен тоже подходит для Bearer-авторизации, но требует обновления после истечения срока. OAuth-токен профиля `yc` не передаётся напрямую в этот API. Для языковых моделей и embeddings предоставьте необходимые роли и разрешения; создавать новый аккаунт, если подходящий ключ уже есть, не требуется.

## Маршруты

| Маршрут | Переменная | API |
| --- | --- | --- |
| `yandex/chat` | `YANDEX_CHAT_MODEL` | Chat и мост Responses → Chat |
| `yandex/lite` | `YANDEX_LITE_MODEL` | Chat и мост Responses → Chat |
| `yandex/embeddings` | `YANDEX_EMBEDDING_MODEL` | Embeddings документов |
| `yandex/embeddings-query` | `YANDEX_QUERY_EMBEDDING_MODEL` | Embeddings поискового запроса |

`yandex_compat.py` добавляет `OpenAI-Project` из `YANDEX_FOLDER_ID` только для `yandex/*`, сохраняя другие заголовки. Неуказанный каталог останавливает запрос до upstream. Клиенту нужен только мастер-ключ LiteLLM, а API-ключ Яндекса хранится на сервере.

NVIDIA-алиасы не переходят в Яндекс при ошибке. Автоматические повторы маршрутизатора (`num_retries: 0`), SDK (`max_retries: 0`) и fallback отключены. Для embeddings также обнулён `DEFAULT_MAX_RETRIES`: в закреплённой версии SDK использует этот default при нулевом значении параметра. Ошибки HTTP 500 проверены офлайн: повторного upstream-запроса нет. Для Responses явно используется Chat bridge LiteLLM; это не проверка нативного Responses API Яндекса. Поддержку tools у конкретной модели подтверждайте отдельно.

## Каталог и проверки

Снимок [catalogs/yandex-catalog.json](catalogs/yandex-catalog.json) содержит полный результат обнаружения с заменой ID каталога на `{folder_id}`. В нём есть текстовые, embedding и speech/realtime модели, включая версии `rc` и `deprecated`. Они не добавляются автоматически как Chat deployments.

Начальные значения `.env.example` взяты из обнаруженного каталога. Наличие в каталоге не подтверждает inference, tools или качество ответа. Живая проверка AliceAI LLM Flash: Chat, Responses, Responses SSE и tools прошли четырьмя согласованными запросами. Другие текстовые модели и embeddings не вызывались. Актуальные результаты: [MODEL_STATUS.md](MODEL_STATUS.md).

Без расходов:

```bash
./validate-repo.sh
./test-offline.sh
```

Офлайн-тесты запускают настоящий LiteLLM 1.93.0 против локальной имитации API внутри Docker без внешней сети. Проверяются Bearer-ключ, OpenAI-Project, полный URI модели, Chat, Responses, SSE, tools и отдельные endpoints для embeddings. Настоящие ключи при этом не используются.

Только после согласования модели и расходов:

```bash
YANDEX_TEST_ALLOW_INFERENCE=1 YANDEX_TEST_MAX_OUTPUT_TOKENS=128 ./test-yandex.sh yandex/chat
```

Скрипт делает ровно четыре клиентских inference-запроса к одному маршруту: Chat, Responses, Responses SSE, Responses tools. Embeddings и другие модели он не вызывает. Значение по умолчанию — 128 выходных токенов на запрос, верхний предел — 256. Повторы клиента нужно отдельно отключить в используемом приложении. Лимит токенов не является точным денежным лимитом провайдера.

После настройки примените конфигурацию только к сервису шлюза; рабочую базу данных сохраняйте. На текущем хосте рабочий шлюз использует другой каталог развёртывания: перенос файлов из этого репозитория сам по себе его не обновляет.

## Источники

- [Официальный SDK и описание OpenAI-совместимого API](https://github.com/yandex-cloud/yandex-ai-studio-sdk)
- [Документация API](https://aistudio.yandex.ru/docs/ai-studio/concepts/api.html)
- [Модели](https://aistudio.yandex.ru/docs/ai-studio/concepts/generation/models.html)

Endpoint этого комплекта подтверждён реальным GET-каталогом. Официальный SDK также использует `https://llm.api.cloud.yandex.net/v1`; он вернул тот же каталог при проверке. Основным остаётся `ai.api.cloud.yandex.net`.
