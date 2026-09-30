# Подключение Codex, Claude Code и OpenCode

Все шаблоны находятся в каталоге `client-configs/` и не содержат секретов.

Перед запуском клиента экспортируйте мастер-ключ LiteLLM:

```bash
export LITELLM_MASTER_KEY='sk-ваш-мастер-ключ'
```

Адреса в шаблонах рассчитаны на запуск клиента непосредственно на Docker-хосте:

- OpenAI API: `http://127.0.0.1:4001/v1`;
- Anthropic Messages API: `http://127.0.0.1:4001`.

Если клиент работает в другом контейнере, замените `127.0.0.1` на доступное ему имя хоста или Docker-сервиса.

## Codex

Шаблон: `client-configs/codex-nim.config.toml`.

Codex использует Responses API. Поэтому в провайдере обязательно указано `wire_api = "responses"`, а `base_url` заканчивается на `/v1`.

Codex также передаёт служебное поле `client_metadata`. NVIDIA NIM его не поддерживает, поэтому `litellm_config.yaml` удаляет это поле через `router_settings.default_litellm_params.additional_drop_params` до отправки запроса провайдеру.

Установите профиль:

```bash
mkdir -p ~/.codex
cp client-configs/codex-nim.config.toml ~/.codex/nim.config.toml
```

Запустите Codex с профилем:

```bash
codex --profile nim
```

Другой алиас можно выбрать на один запуск:

```bash
codex --profile nim --model nim/code
codex --profile nim --model nim/reasoning
```

Для локальных моделей подготовлены отдельные профили с подходящими таймаутами и контекстом:

```bash
cp client-configs/codex-ollama.config.toml ~/.codex/ollama.config.toml
cp client-configs/codex-lmstudio.config.toml ~/.codex/lmstudio.config.toml

codex --profile ollama
codex --profile lmstudio

codex --profile ollama --model ollama/gemma3:12b
codex --profile lmstudio --model lmstudio/granite-4.0-h-tiny
```

Профиль `lmstudio` проверен с `granite-4.0-h-tiny` и контекстом `248064`; для другой модели измените `model_context_window`. Доступные динамические имена показывает `./test-local-models.sh --catalog`.

Чтобы сделать LiteLLM провайдером по умолчанию, перенесите параметры шаблона в `~/.codex/config.toml`. Не помещайте `model_provider` и `model_providers` в проектный `.codex/config.toml`: Codex игнорирует перенаправление провайдера из проектного конфига.

Проверка без интерактивного интерфейса:

```bash
codex exec --profile nim --ephemeral --skip-git-repo-check \
  'Ответь только: CODEX_NIM_OK'
```

Официальная документация:

- [Custom model providers](https://learn.chatgpt.com/docs/config-file/config-advanced#custom-model-providers)
- [Profiles](https://learn.chatgpt.com/docs/config-file/config-advanced#profiles)

## Claude Code

Шаблон: `client-configs/claude-nim.settings.json`.

LiteLLM принимает запросы Claude Code через Anthropic Messages API `/v1/messages`. Для bearer-аутентификации Claude Code ожидает переменную `ANTHROPIC_AUTH_TOKEN`, поэтому перед запуском свяжите её с мастер-ключом LiteLLM:

```bash
export ANTHROPIC_AUTH_TOKEN="$LITELLM_MASTER_KEY"
claude --settings "$PWD/client-configs/claude-nim.settings.json"
```

Проверка в неинтерактивном режиме:

```bash
export ANTHROPIC_AUTH_TOKEN="$LITELLM_MASTER_KEY"
claude --settings "$PWD/client-configs/claude-nim.settings.json" \
  --model nim/agent \
  --no-session-persistence \
  -p 'Ответь только: CLAUDE_NIM_OK'
```

Чтобы применять настройки постоянно, объедините содержимое шаблона со своим `~/.claude/settings.json`. Сам ключ лучше оставить в окружении или менеджере секретов. Если всё же записываете его в настройки, добавьте в `env` поле `ANTHROPIC_AUTH_TOKEN` и никогда не коммитьте этот файл.

Шаблон намеренно перенаправляет встроенные семейства `opus`, `sonnet`, `haiku` и субагентов на `nim/agent`. Это не даёт Claude Code случайно отправить в LiteLLM отсутствующий идентификатор `claude-*`.

Автоматическое обнаружение моделей Claude Code здесь не используется: официальный механизм `/v1/models` показывает только идентификаторы, начинающиеся с `claude` или `anthropic`, а наши алиасы начинаются с `nim/`.

Важное ограничение: Anthropic официально поддерживает LLM gateway в формате Messages API, но не поддерживает использование Claude Code с не-Claude моделями. Связка с NVIDIA NIM является совместимой на уровне API, но отдельные новые функции Claude Code могут потребовать обновления LiteLLM или защитных флагов. В шаблоне отключены экспериментальные beta-поля и adaptive thinking, поскольку произвольные NIM-модели могут их не понимать.

Проверка маршрута внутри Claude Code:

```text
/status
```

В статусе должны отображаться `Anthropic base URL: http://127.0.0.1:4001` и источник токена `ANTHROPIC_AUTH_TOKEN`.

Официальная документация:

- [Connect Claude Code to an LLM gateway](https://code.claude.com/docs/en/llm-gateway-connect)
- [Gateway protocol](https://code.claude.com/docs/en/llm-gateway-protocol)
- [Model configuration](https://code.claude.com/docs/en/model-config)

## OpenCode

Шаблон: `client-configs/opencode-nim.json`.

Разовый запуск без изменения пользовательского конфига:

```bash
OPENCODE_CONFIG="$PWD/client-configs/opencode-nim.json" opencode
```

Немедленно открыть конкретную модель:

```bash
OPENCODE_CONFIG="$PWD/client-configs/opencode-nim.json" \
  opencode --model litellm-nim/nim/agent
```

Проверка без TUI:

```bash
OPENCODE_CONFIG="$PWD/client-configs/opencode-nim.json" \
  opencode run --model litellm-nim/nim/agent \
  'Ответь только: OPENCODE_NIM_OK'
```

Для постоянной установки скопируйте или объедините шаблон с глобальным конфигом:

```bash
mkdir -p ~/.config/opencode
cp client-configs/opencode-nim.json ~/.config/opencode/opencode.json
```

Если `~/.config/opencode/opencode.json` уже существует, не перезаписывайте его: перенесите из шаблона секцию `provider.litellm-nim`, а также поля `model` и `small_model`.

OpenCode подставляет ключ из окружения благодаря записи `{env:LITELLM_MASTER_KEY}`. В `/models` провайдер отображается как `LiteLLM NVIDIA NIM`.

`nim/fast` используется только как `small_model` для заголовков и других коротких фоновых задач. Для него намеренно указан консервативный предел в 4096 входных и 1024 выходных токена: это ограничение фоновых задач клиента, а не измеренный предел всех моделей текущего пула.

Официальная документация:

- [Providers and custom OpenAI-compatible providers](https://opencode.ai/docs/providers/)
- [Config locations and environment variables](https://opencode.ai/docs/config/)

## Что проверено на этом комплекте

- Codex: Responses API, SSE streaming, function calling и возврат результата инструмента;
- Claude Code: реальный запуск CLI через `/v1/messages` и двухшаговый вызов инструмента;
- OpenCode: OpenAI-совместимый провайдер, выбор алиаса и агентный запрос.

Основной рекомендуемый NVIDIA-алиас для всех трёх клиентов — `nim/agent`.

Локальные модели Ollama и LM Studio через тот же прокси описаны в [LOCAL_MODELS_RU.md](LOCAL_MODELS_RU.md).

## Cloud.ru через тот же шлюз

Выбирайте точный маршрут `cloudru/<ID>`, например `cloudru/Qwen/Qwen3-Coder-Next`. Ключ Cloud.ru хранится только в окружении серверного LiteLLM; клиенту нужен `LITELLM_MASTER_KEY`. Алиасы `nim/*` всегда остаются на NVIDIA и не переходят в Cloud.ru при ошибке.

Для Codex доступен мост Responses → Chat Completions с hook `cloudru_compat.py`, сохраняющим порядок tool history. Его регрессии проверяются без сети; текущие живые Responses/SSE Cloud.ru не тестировались. При выборе платной модели отдельно настройте лимиты и повторы клиента: `request_max_retries` / `stream_max_retries` в NVIDIA-шаблоне не управляются `num_retries: 0` на шлюзе.

Для текущего развёртывания подготовлены [client-configs/codex-cloudru.config.toml](client-configs/codex-cloudru.config.toml) и [client-configs/codex-cloudru.models.json](client-configs/codex-cloudru.models.json). Они используют шесть старых точных имён маршрутов, сохранённых в рабочем шлюзе и конфигурации проекта. Эти маршруты всегда идут в Cloud.ru, даже без префикса `cloudru/`.

```bash
mkdir -p ~/.codex/model-catalogs
cp client-configs/codex-cloudru.models.json ~/.codex/model-catalogs/cloudru-models.json
cp client-configs/codex-cloudru.config.toml ~/.codex/cloudru-gateway.config.toml
# LITELLM_MASTER_KEY должен быть экспортирован, как описано в начале документа.
codex --profile cloudru-gateway
```

По умолчанию — `ai-sage/GigaChat3-10B-A1.8B`. В `/model` доступны GigaChat3, GigaChat3.5, DeepSeek V4 Pro, Kimi K2.6, GLM 5.1 и MiniMax M3. MiniMax помечен прежним таймаутом; добавление в меню не подтверждает работоспособность. Расширенные `cloudru/*` маршруты проекта добавляются в клиентский каталог только после их применения к конкретному шлюзу. Клиентский контекст ограничен 32768 токенами, HTTP/SSE-повторы отключены. Для другой модели upstream это не заявление о её максимальном контексте.

Имя `cloudru-gateway` отличает этот профиль от возможного `cloudru` с прямым подключением к провайдеру. Существующие прямые профили и их ключи не требуется менять или переносить в проект.

Профиль и локальный каталог проверены Codex 0.159.2 без генерации. Новых запросов к Cloud.ru не выполнялось; живые Responses/SSE и агентная сессия с этим профилем не проверялись. Ключ провайдера не записывается в клиентские файлы.

## Яндекс AI Studio

Модель выбирается явно: `yandex/chat` или `yandex/lite`. Серверный LiteLLM хранит API-ключ Яндекса и ID каталога в окружении; клиент использует `LITELLM_MASTER_KEY`. Для Responses применяется мост в Chat Completions. Возможность работы с инструментами зависит от выбранной модели; живые результаты указаны в [MODEL_STATUS.md](MODEL_STATUS.md).

Для Codex подготовлен отдельный профиль [client-configs/codex-yandex.config.toml](client-configs/codex-yandex.config.toml). Он выбирает `yandex/chat` (AliceAI LLM Flash при стандартных настройках шлюза), использует Responses API и отключает HTTP/SSE-повторы клиента. `num_retries: 0` на шлюзе само по себе не управляет повторами Codex.

```bash
mkdir -p ~/.codex/model-catalogs
cp client-configs/codex-yandex.models.json ~/.codex/model-catalogs/yandex-models.json
cp client-configs/codex-yandex.config.toml ~/.codex/yandex.config.toml
# LITELLM_MASTER_KEY должен быть экспортирован, как описано в начале документа.
codex --profile yandex
```

По умолчанию выбран `yandex/chat` → AliceAI LLM Flash (`latest`). В консоли команда `/model` открывает отдельный список из [client-configs/codex-yandex.models.json](client-configs/codex-yandex.models.json): AliceAI LLM Flash (`yandex/chat`) и YandexGPT Lite (`yandex/lite`, не проверена). Список содержит только два настроенных chat-маршрута; embeddings и speech/realtime для этого меню не подходят. Если upstream маршрута изменён в `.env`, обновите его отображаемое имя в JSON.

`model_catalog_json` задаёт локальный каталог для выбранного профиля. Он не создаёт маршруты на шлюзе и не подтверждает возможности модели: обычный `/v1/models` не содержит всех метаданных, которые нужны Codex. Каталог содержит краткие общие инструкции ассистенту и консервативные параметры клиента. Для другого провайдера можно подготовить свой JSON и указать его в соответствующем `*.config.toml`; остальные профили при этом сохраняют свои каталоги. Настройка проверена с Codex 0.159.2 без генерации.

API-ключ Яндекса и ID каталога нужны только шлюзу. В профиль они не записываются. Адрес `127.0.0.1:4001` рассчитан на Codex на Docker-хосте; для другого компьютера используйте доступный ему адрес или SSH-туннель. Профиль содержит консервативный клиентский предел контекста 32768 токенов с компактизацией на 24000; это не утверждение о максимальном контексте провайдера.

Reasoning metadata, встроенный web search, WebSocket transport и сжатие запросов отключены для совместимости. Chat, Responses, SSE и function calling Flash прошли согласованные живые проверки; полная агентная сессия Codex и цикл выполнения его инструментов с Яндексом пока не проверялись. Запуск Codex отправляет платные запросы. Полная настройка шлюза: [YANDEX_RU.md](YANDEX_RU.md).
