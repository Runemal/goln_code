# Развёртывание на другой системе

Эта инструкция рассчитана на чистую Linux-систему с Docker. Секреты, PostgreSQL volume и загруженные модели в репозиторий не входят.

## 1. Скопировать проект

```bash
git clone <адрес-репозитория> litellm-gateway
cd litellm-gateway
```

Можно передать каталог архивом, но не включайте `.env`, логи и данные Docker volumes.

## 2. Установить зависимости

Обязательно:

- Docker Engine;
- Docker Compose v2 (`docker compose`);
- `curl`, `jq` и Python 3.11+ для проверок.

Опционально:

- Ollama для `local/ollama`;
- LM Studio и `lms` CLI для `local/lmstudio`;
- ImageMagick и ffmpeg для `test-multimodal.sh`;
- Codex CLI для сквозной агентной проверки.

## 3. Создать окружение

```bash
cp .env.example .env
chmod 600 .env
```

Обязательно замените:

```dotenv
LITELLM_MASTER_KEY=sk-уникальный-длинный-ключ
POSTGRES_PASSWORD=длинный-url-безопасный-пароль
```

Для NVIDIA NIM укажите настоящий `NVIDIA_NIM_API_KEY`. Если используются только локальные модели, можно оставить заглушку.

Для локальных моделей замените `OLLAMA_MODEL` и `LM_STUDIO_MODEL` на ID, реально установленные на новой машине. Подробности: [LOCAL_MODELS_RU.md](LOCAL_MODELS_RU.md).

## 4. Статическая проверка

```bash
./validate-repo.sh
```

Проверка не обращается к API моделей и не требует запущенного стека.

## 5. Запуск

Сначала запустите настроенные локальные провайдеры. Для LM Studio откройте приложение, включите Local Server и явно загрузите модель с нужным контекстом; JIT после перезапуска может использовать значение по умолчанию. Команды для проверенной Granite-конфигурации приведены в [LOCAL_MODELS_RU.md](LOCAL_MODELS_RU.md#контекст-granite).

```bash
docker compose pull
docker compose up -d
docker compose ps
```

Первый старт может занять несколько минут из-за инициализации PostgreSQL. Дождитесь состояния `healthy`:

```bash
docker compose logs --tail=100 litellm
curl -fsS http://127.0.0.1:${LITELLM_PORT:-4001}/health/liveliness
```

## 6. Smoke-тесты

NVIDIA-текст и tools:

```bash
./test-models.sh
```

Responses API Codex:

```bash
./test-responses.sh
```

Локальные модели:

```bash
./test-local-models.sh --catalog
./test-local-models.sh local/ollama
./test-local-models.sh local/lmstudio
```

`--catalog` проверяет автоматическое обнаружение без последовательной загрузки всех моделей. Полные smoke-тесты запускайте только для настроенных и совместимых провайдеров.

## 7. Codex

```bash
mkdir -p ~/.codex
cp client-configs/codex-nim.config.toml ~/.codex/nim.config.toml
cp client-configs/codex-ollama.config.toml ~/.codex/ollama.config.toml
cp client-configs/codex-lmstudio.config.toml ~/.codex/lmstudio.config.toml
export LITELLM_MASTER_KEY='sk-значение-из-.env'
```

Примеры:

```bash
codex --profile nim
codex --profile ollama
codex --profile lmstudio
```

Не копируйте `model_provider` и `model_providers` в проектный `.codex/config.toml`: Codex разрешает эти параметры в пользовательском или профильном конфиге.

## 8. Что не переносится автоматически

- `.env` и API-ключи;
- PostgreSQL volume и история LiteLLM;
- модели Ollama;
- загруженные модели и настройки контекста LM Studio;
- пользовательские конфиги Codex, Claude Code и OpenCode;
- правила firewall.

Если нужна миграция истории LiteLLM, отдельно экспортируйте PostgreSQL. Обычный перенос репозитория создаёт чистую базу.

После каждого переноса или перезапуска проверяйте фактический контекст LM Studio командой `lms ps --json`: значение в профиле Codex не загружает модель и не меняет её серверную конфигурацию.

## 9. Критерии готовности

- `docker compose ps` показывает `db` и `litellm` как healthy;
- `/health/liveliness` возвращает HTTP 200;
- `/v1/models` доступен с `LITELLM_MASTER_KEY`;
- выбранный smoke-тест завершился с кодом 0;
- Codex вернул контрольную строку через нужный профиль.
