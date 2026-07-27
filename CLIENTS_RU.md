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

`nim/fast` используется только как `small_model` для заголовков и других коротких фоновых задач. Для него намеренно указан консервативный предел в 4096 входных и 1024 выходных токена: среди быстрых NVIDIA deployments есть модель с небольшим контекстным окном.

Официальная документация:

- [Providers and custom OpenAI-compatible providers](https://opencode.ai/docs/providers/)
- [Config locations and environment variables](https://opencode.ai/docs/config/)

## Что проверено на этом комплекте

- Codex: Responses API, SSE streaming, function calling и возврат результата инструмента;
- Claude Code: реальный запуск CLI через `/v1/messages` и двухшаговый вызов инструмента;
- OpenCode: OpenAI-совместимый провайдер, выбор алиаса и агентный запрос.

Основной рекомендуемый NVIDIA-алиас для всех трёх клиентов — `nim/agent`.

Локальные модели Ollama и LM Studio через тот же прокси описаны в [LOCAL_MODELS_RU.md](LOCAL_MODELS_RU.md).
