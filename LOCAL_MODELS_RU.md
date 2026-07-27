# Codex через LiteLLM с Ollama и LM Studio

LiteLLM предоставляет единый Responses API для облачных и локальных моделей:

```text
Codex → http://127.0.0.1:4001/v1 → LiteLLM в Docker
                                      ├─ host.docker.internal:11434 → Ollama
                                      └─ host.docker.internal:1234  → LM Studio
```

Стабильные алиасы:

- `local/ollama` → значение `OLLAMA_MODEL`;
- `local/lmstudio` → значение `LM_STUDIO_MODEL`.

Динамические маршруты:

- `ollama/<имя>` → любая установленная модель Ollama;
- `lmstudio/<id>` → любая модель, опубликованная LM Studio.

Примеры: `ollama/gemma3:12b`, `ollama/yandex/YandexGPT-5-Lite-8B-instruct-GGUF:latest`, `lmstudio/granite-4.0-h-tiny`.

Префикс LiteLLM входит в model ID: `ollama_chat/gemma4:latest` и `openai/granite-4.0-h-tiny`.

## Динамический каталог

LiteLLM опрашивает `/api/tags` Ollama и `/v1/models` LM Studio при формировании списка моделей. После установки новой модели менять `litellm_config.yaml` не требуется.

```bash
./test-local-models.sh --catalog
./test-local-models.sh --catalog ollama
./test-local-models.sh --catalog lmstudio
```

Проверка каталога не загружает последовательно все модели в VRAM. Она подтверждает обнаружение и маршрутизацию имён; поддержку Chat, Responses и tools проверяйте отдельно только для выбранных моделей.

LM Studio также публикует embedding-модели, например `lmstudio/text-embedding-nomic-embed-text-v1.5`. Их вызывают через `/v1/embeddings`, а не через Chat или Codex.

## Общая сетевая настройка

`127.0.0.1` внутри контейнера указывает на сам контейнер. Compose добавляет `host.docker.internal` через `host-gateway`, поэтому сервер модели на Linux должен слушать не только loopback-интерфейс.

Проверьте порты:

```bash
ss -ltn | grep -E '11434|1234'
```

Для Docker ожидаются `0.0.0.0:11434`, `*:11434`, `0.0.0.0:1234` или эквивалентная привязка к интерфейсу Docker-хоста.

## Ollama

### Определение способа установки

```bash
command -v ollama
ollama --version
systemctl status ollama --no-pager
```

Если Ollama работает как systemd-сервис, создайте переносимый override без интерактивного редактора:

```bash
printf '[Service]\nEnvironment="OLLAMA_HOST=0.0.0.0:11434"\n' |
  sudo systemctl edit --stdin ollama

sudo systemctl daemon-reload
sudo systemctl restart ollama
```

Проверка:

```bash
systemctl show ollama -p Environment --no-pager
ss -ltn | grep 11434
curl -fsS http://127.0.0.1:11434/api/tags | jq -r '.models[].name'
```

Настройки LiteLLM в `.env`:

```dotenv
OLLAMA_MODEL=ollama_chat/gemma4:latest
OLLAMA_API_BASE=http://host.docker.internal:11434
```

Замените `gemma4:latest` на точное имя из `/api/tags`.

Ollama по умолчанию не требует токен. Порт `11434`, открытый на `0.0.0.0`, ограничьте firewall для недоверенных сетей.

## LM Studio

### Настройки Local Server

Рекомендуемая конфигурация:

- Server Port: `1234`;
- «Обслуживание по локальной сети»: включено;
- CORS: не требуется для LiteLLM;
- Allow per-request MCPs: выключено, если специально не используется;
- Allow calling servers from `mcp.json`: выключено, если специально не используется;
- JIT loading: по желанию;
- автоматическая разгрузка JIT: включена при совместной работе с Ollama;
- сохранять только последнюю JIT-модель: включено;
- TTL: обычно 10–15 минут удобнее, чем 60 минут.

После перезагрузки системы сначала запустите приложение LM Studio. Если daemon уже работает, сервер можно включить из CLI:

```bash
lms server start
lms server status
```

После изменения сетевой настройки перезапустите Local Server и проверьте:

```bash
ss -ltn | grep 1234
curl -fsS http://127.0.0.1:1234/v1/models | jq -r '.data[].id'
```

Если отключена `Require Authentication`, настоящий токен не нужен. LiteLLM всё равно получает непустую техническую заглушку:

```dotenv
LM_STUDIO_MODEL=openai/granite-4.0-h-tiny
LM_STUDIO_API_BASE=http://host.docker.internal:1234/v1
LM_STUDIO_API_KEY=lm-studio
```

Если `Require Authentication` включена, замените `LM_STUDIO_API_KEY` настоящим ключом и не публикуйте `.env`.

Значение `LM_STUDIO_MODEL` должно состоять из префикса `openai/` и точного `id`, возвращённого `/v1/models`. Не оставляйте `replace-with-loaded-model-id`: с одной загруженной моделью LM Studio может принять такой запрос, но JIT и переключение нескольких моделей будут непредсказуемы.

### Контекст Granite

Проверенная локальная конфигурация `granite-4.0-h-tiny`:

- контекст LM Studio: `248064` токена;
- размер модели: около 4,23 ГБ;
- суммарное наблюдаемое использование RTX 3060 12 ГБ: около 7,7 ГБ;
- Chat Completions, Responses API, tool calling и Codex: успешно.

JIT-загрузка может вернуть модель к стандартному контексту `8192` после перезапуска или автоматической выгрузки. Для воспроизводимой загрузки явно задайте контекст:

```bash
lms unload --all
lms load granite-4.0-h-tiny \
  --context-length 248064 \
  --gpu max \
  --identifier granite-4.0-h-tiny \
  --yes

lms ps --json | jq '.[] | {identifier, contextLength, status}'
```

Команда `lms ps` должна показать `"contextLength": 248064`. Настройка `model_context_window` в профиле Codex описывает уже доступное окно, но сама не меняет контекст, с которым LM Studio загрузила модель.

Это не универсальное значение. На другой видеокарте уменьшите контекст, parallel requests или GPU offload, если модель не загружается либо система начинает использовать swap.

## Применение `.env`

После изменения model ID или ключа пересоздайте контейнер LiteLLM:

```bash
docker compose up -d --force-recreate litellm
docker compose ps
```

`docker compose restart` не перечитывает `.env`.

## Автоматические проверки

Все локальные маршруты:

```bash
./test-local-models.sh
```

Только один провайдер:

```bash
./test-local-models.sh local/ollama
./test-local-models.sh local/lmstudio
```

Динамические каталоги без тяжёлого inference:

```bash
./test-local-models.sh --catalog
```

Расширенная регрессия Responses API и SSE:

```bash
CODEX_TEST_MODEL=local/ollama REQUEST_TIMEOUT=300 ./test-responses.sh
CODEX_TEST_MODEL=local/lmstudio REQUEST_TIMEOUT=300 ./test-responses.sh
```

## Профили Codex

Codex 0.134.0 и новее загружает именованный профиль из `~/.codex/<имя>.config.toml`.

```bash
mkdir -p ~/.codex
cp client-configs/codex-ollama.config.toml ~/.codex/ollama.config.toml
cp client-configs/codex-lmstudio.config.toml ~/.codex/lmstudio.config.toml

export LITELLM_MASTER_KEY='sk-ваш-мастер-ключ'
codex --profile ollama
codex --profile lmstudio

# Выбор конкретной модели из динамического каталога:
codex --profile ollama --model ollama/gemma3:12b
codex --profile lmstudio --model lmstudio/granite-4.0-h-tiny
```

Проверка без TUI:

```bash
codex exec --profile ollama --ephemeral --skip-git-repo-check \
  'Ответь только: CODEX_OLLAMA_OK'

codex exec --profile lmstudio --ephemeral --skip-git-repo-check \
  'Ответь только: CODEX_LMSTUDIO_OK'
```

В профиле LM Studio указан проверенный контекст `248064`. Для другой модели измените `model_context_window` на фактическое значение. Профиль Ollama содержит консервативные `32768` токенов.

## Видеопамять

На RTX 3060 12 ГБ два экземпляра LM Studio занимали около 9 ГБ и вызывали падение `gemma4` в Ollama с `GGML_ASSERT`. После выгрузки LM Studio модель Ollama заработала.

Для освобождения моделей LM Studio:

```bash
lms unload --all
```

Не рассчитывайте на одновременную работу нескольких крупных моделей на одной 12-ГБ видеокарте. Для предсказуемых тестов оставляйте загруженной одну модель.

## Диагностика

| Симптом | Причина | Проверка или решение |
| --- | --- | --- |
| Docker получает `Connection refused` | сервер слушает `127.0.0.1` | включить LAN-доступ, проверить `ss -ltn` |
| LM Studio отвечает HTTP 401 | включена аутентификация | указать настоящий `LM_STUDIO_API_KEY` или отключить auth |
| LiteLLM вызывает не ту модель | placeholder или неверный ID | проверить `/v1/models`, обновить `LM_STUDIO_MODEL` |
| `ollama/*` или `lmstudio/*` не видны | локальный endpoint недоступен из Docker | проверить LAN-привязку, затем `./test-local-models.sh --catalog` |
| После перезапуска контекст снова `8192` | JIT загрузил модель с настройками по умолчанию | явно выполнить `lms load ... --context-length 248064` и проверить `lms ps --json` |
| Ollama падает при загрузке | занята VRAM | `nvidia-smi`, `lms ps`, выгрузить лишние модели |
| Responses имеет `status=incomplete` | слишком мал `max_output_tokens` | использовать не менее 256 для reasoning-моделей |
| Codex предупреждает о fallback metadata | локального ID нет во встроенном каталоге Codex | явно задать `model_context_window` в профиле |

Официальная документация Codex по профилям и custom providers: [Advanced Configuration](https://learn.chatgpt.com/docs/config-file/config-advanced).
