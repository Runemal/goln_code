# LiteLLM gateway для NVIDIA NIM, Ollama и LM Studio

Переносимый комплект для единого OpenAI-совместимого прокси: LiteLLM, PostgreSQL, NVIDIA NIM и локальные модели на Docker-хосте. Проверены Chat Completions, Responses API Codex, streaming и function calling.

## Что входит в комплект

- `docker-compose.yml` — LiteLLM и PostgreSQL;
- `litellm_config.yaml` — точные NVIDIA model id, стабильные алиасы и динамические локальные каталоги;
- `.env.example` — шаблон переменных окружения без секретов;
- `test-models.sh` — проверка текста, алиасов и function calling;
- `test-responses.sh` — регрессия Codex Responses API, SSE и `client_metadata`;
- `test-local-models.sh` — проверка каталогов, Chat Completions, Responses API и tools для Ollama/LM Studio;
- `test-multimodal.sh` — проверка изображений, OCR, видео и аудио;
- `validate-repo.sh` — статическая проверка конфигов перед публикацией;
- `CURL_EXAMPLES.md` — готовые curl-команды;
- `MODEL_STATUS.md` — результаты проверки каталога NVIDIA.
- `CLIENTS_RU.md` — подключение Codex, Claude Code и OpenCode;
- `LOCAL_MODELS_RU.md` — Ollama и LM Studio через тот же LiteLLM;
- `DEPLOYMENT_RU.md` — развёртывание каталога на чистой системе;
- `client-configs/` — готовые шаблоны конфигурации клиентов без секретов.

## Провайдеры и алиасы

| Маршрут | Источник |
| --- | --- |
| `local/ollama` | модель `OLLAMA_MODEL` на Docker-хосте |
| `local/lmstudio` | модель `LM_STUDIO_MODEL` на Docker-хосте |
| `ollama/*` | любая модель из живого `/api/tags` Ollama |
| `lmstudio/*` | любая модель из живого `/v1/models` LM Studio |
| `nim/*` | NVIDIA NIM API |

Стабильные `local/*` алиасы предназначены для заранее проверенных профилей Codex. Wildcard-маршруты позволяют обращаться к конкретной модели, например `ollama/gemma4:latest` или `lmstudio/granite-4.0-h-tiny`, без добавления каждой записи в YAML.

Удобные NVIDIA-алиасы:

| Алиас | Назначение |
| --- | --- |
| `nim/fast` | быстрые универсальные запросы |
| `nim/chat` | обычный диалог |
| `nim/agent` | агенты и вызов инструментов |
| `nim/code` | программирование и вызов инструментов |
| `nim/reasoning` | сложные задачи с рассуждением |
| `nim/vision` | понимание изображений |
| `nim/ocr` | OCR с обычным текстовым ответом |
| `nim/ocr-structured` | OCR с координатами блоков через `markdown_bbox` |
| `nim/omni` | изображения, видео, аудио и текст |

Внутри алиаса находится несколько проверенных NVIDIA deployments. LiteLLM выбирает один deployment по измеренной задержке. Запрос не рассылается всем моделям одновременно.

При временной ошибке применяется одна повторная попытка. После двух ошибок deployment исключается из маршрутизации на 60 секунд.

## Требования

- Docker и Docker Compose;
- `curl` и `jq` для обычной проверки;
- Python 3.11+ для `validate-repo.sh`;
- `ImageMagick` и `ffmpeg` для мультимодальной проверки.

Ollama и LM Studio устанавливаются на Docker-хост отдельно и нужны только для соответствующих локальных маршрутов.

## Настройка и запуск

```bash
cp .env.example .env
chmod 600 .env
```

Заполните в `.env`:

```dotenv
NVIDIA_NIM_API_KEY=nvapi-...
LITELLM_MASTER_KEY=sk-...
POSTGRES_PASSWORD=длинный-url-безопасный-пароль
LITELLM_PORT=4001
```

Если нужны только локальные модели, `NVIDIA_NIM_API_KEY` можно оставить заглушкой. Для Ollama и LM Studio обязательно замените model ID и настройте доступ с Docker-хоста по инструкции [LOCAL_MODELS_RU.md](LOCAL_MODELS_RU.md).

Запустите стек:

```bash
docker compose up -d
docker compose ps
```

В `.env.example` закреплён digest образа LiteLLM 1.93.0, на котором выполнены проверки. Обновляйте `LITELLM_IMAGE` только вместе с повторным запуском smoke-тестов.

Первый запуск может занять несколько минут: LiteLLM создаёт схему PostgreSQL.

## Адреса

- API: `http://127.0.0.1:4001/v1`
- Web UI: `http://127.0.0.1:4001/ui/`
- Пользователь UI: `admin`
- Пароль UI: значение `LITELLM_MASTER_KEY`

Порт меняется переменной `LITELLM_PORT`.

## Проверка

Текстовые алиасы и вызов инструментов:

```bash
./test-models.sh
```

Совместимость с Codex Responses API:

```bash
./test-responses.sh
```

Локальные маршруты:

```bash
./test-local-models.sh
./test-local-models.sh local/ollama
./test-local-models.sh local/lmstudio
./test-local-models.sh --catalog
```

Изображения, OCR, видео и аудио:

```bash
./test-multimodal.sh
```

Все smoke-тесты возвращают ненулевой код завершения, если хотя бы одна проверка не пройдена.

Статическая проверка перед коммитом:

```bash
./validate-repo.sh
```

## Пример запроса

```bash
curl http://127.0.0.1:4001/v1/chat/completions \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "nim/fast",
    "messages": [
      {"role": "user", "content": "Кратко объясни назначение NVIDIA NIM."}
    ],
    "max_tokens": 256
  }' | jq
```

Больше примеров: [CURL_EXAMPLES.md](CURL_EXAMPLES.md).

Подключение агентных клиентов: [CLIENTS_RU.md](CLIENTS_RU.md).

Подключение Ollama и LM Studio: [LOCAL_MODELS_RU.md](LOCAL_MODELS_RU.md).

Развёртывание копии каталога на другой машине: [DEPLOYMENT_RU.md](DEPLOYMENT_RU.md).

## Мультимодальные возможности

Через `/v1/chat/completions` проверены:

- распознавание и описание изображений;
- обычный и структурированный OCR;
- анализ видео;
- понимание аудио.

В доступном текущему NVIDIA-аккаунту каталоге нет отдельных text-to-image, text-to-video, ASR и TTS endpoints. Они намеренно не добавлены в конфиг как несуществующие маршруты.

## Обновление и управление

```bash
docker compose pull litellm
docker compose up -d --force-recreate litellm
docker compose logs -f litellm
docker compose restart litellm
docker compose down
```

`docker compose down` сохраняет PostgreSQL volume. Команда `docker compose down -v` удаляет сохранённые данные.

После изменения `.env` используйте `docker compose up -d --force-recreate litellm`: обычный `restart` не перечитывает переменные окружения.

## Безопасность

- Не добавляйте `.env` в Git.
- Не храните NVIDIA API key в YAML или shell-скриптах.
- Используйте мастер-ключ LiteLLM, начинающийся с `sk-`.
- Для внешнего доступа разместите перед LiteLLM HTTPS reverse proxy.
- Порты Ollama и LM Studio, открытые на `0.0.0.0`, ограничьте firewall. Если LM Studio доступна по недоверенной сети, включите API token.
- Не включайте удалённые MCP-функции LM Studio, если они не нужны: Codex передаёт инструменты через LiteLLM независимо от встроенного MCP LM Studio.
