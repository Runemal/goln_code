# LiteLLM gateway: NVIDIA NIM, Cloud.ru, Яндекс AI Studio, Ollama и LM Studio

Переносимый OpenAI-совместимый прокси на LiteLLM 1.93.0 и PostgreSQL. Каталоги и результаты проверок обновлены **30 сентября 2026 года**. Текущий статус и ограничения: [MODEL_STATUS.md](MODEL_STATUS.md).

## Маршруты

| Маршрут | Провайдер и назначение |
| --- | --- |
| Точный NVIDIA ID, например `openai/gpt-oss-20b` | NVIDIA NIM |
| `nim/fast`, `nim/chat` | NVIDIA: быстрый ответ и диалог |
| `nim/agent`, `nim/code` | NVIDIA: модели с успешно проверенными tools |
| `nim/reasoning` | NVIDIA Nemotron Ultra |
| `nim/vision`, `nim/ocr` | NVIDIA: изображения и обычный OCR |
| `nim/ocr-structured` | NVIDIA Nemotron Parse: изображение без текстовой части |
| `nim/omni` | NVIDIA Omni; видео и аудио в текущей проверке вернули 503 |
| `nim/embeddings` | NVIDIA Nemotron 3 Embed, `/v1/embeddings` |
| `cloudru/<ID>` | Cloud.ru, только явно выбранная модель |
| `cloudru/BAAI/bge-m3` | Cloud.ru embeddings, платный запрос |
| `yandex/chat`, `yandex/lite`, другие `yandex/*` | 12 текстовых моделей Яндекс AI Studio, явный выбор |
| `yandex/embeddings`, `yandex/embeddings-query` | Яндекс: документы и поисковые запросы |
| `local/ollama`, `local/lmstudio` | Модель из переменных `OLLAMA_MODEL` / `LM_STUDIO_MODEL` |
| `ollama/*`, `lmstudio/*` | Динамический каталог локального провайдера |

Например, `cloudru/Qwen/Qwen3-Coder-Next` направляется в Cloud.ru, а `ollama/gemma4:12b` — в локальную Ollama. Шесть старых точных Cloud.ru ID сохранены для совместимости существующих клиентов; полный список есть в [MODEL_STATUS.md](MODEL_STATUS.md).

Cloud.ru не входит в алиасы `nim/*` и не используется как запасной провайдер. Автоматические повторы маршрутизатора и SDK отключены (`num_retries: 0`, `max_retries: 0`), чтобы ошибка не запускала дополнительный inference-запрос. Клиентские повторы настраиваются отдельно.

Настройка и статус Яндекса: [YANDEX_RU.md](YANDEX_RU.md). Его маршруты используют API-ключ из окружения и не входят в NVIDIA-алиасы или автоматические fallback.

NVIDIA-алиас содержит один или несколько deployments; маршрутизатор выбирает одну модель по измеренной задержке. Полные каталоги находятся в [catalogs/](catalogs/): 81 NVIDIA ID, 95 Cloud.ru ID и 27 Яндекс ID. У Яндекса полный URI включает ID каталога; в снимке он скрыт. Наличие ID в каталоге не подтверждает доступность inference. Для Яндекса добавлены 12 обычных текстовых `latest`-моделей; живыми запросами проверена только AliceAI LLM Flash. Speech/realtime, embeddings, `rc` и `deprecated` не входят в меню Codex.

## Настройка

Нужны Docker и Compose v2. Для проверок: `curl`, `jq`, Python 3.11+ и PyYAML (`python3 -m pip install PyYAML==6.0.3`). Для мультимодальных тестов дополнительно нужны ImageMagick и ffmpeg. Локальные серверы устанавливаются отдельно.

```bash
cp .env.example .env
chmod 600 .env
```

Замените `LITELLM_MASTER_KEY` и `POSTGRES_PASSWORD`. Для NVIDIA заполните `NVIDIA_NIM_API_KEY`, для Cloud.ru — `CLOUDRU_API_KEY`, для Яндекса — `YANDEX_API_KEY` и `YANDEX_FOLDER_ID`; неиспользуемые облачные ключи можно оставить заглушками. Укажите реально установленную модель Ollama и/или загруженную модель LM Studio. На проверенном хосте установлены `gemma4:12b` и `qwen3.5:9b-q8_0`, а LM Studio сейчас выключена.

`NVIDIA_NIM_API_BASE` и `CLOUDRU_API_BASE` задают upstream URL. По умолчанию это публичные API провайдеров. На проверенном хосте прямой NVIDIA API отвечает HTTP 451; успешные NVIDIA-проверки выполнены через временный SSH-туннель с разрешённого сервера. Туннель не входит в комплект. До запуска облачных маршрутов проверьте доступность API из вашей сети.

```bash
./validate-repo.sh
docker compose up -d
docker compose ps
```

Образ LiteLLM закреплён по digest в Compose и `.env.example`; это версия 1.93.0. Первый запуск инициализирует базу PostgreSQL. API по умолчанию слушает `http://127.0.0.1:4001/v1`, UI — `http://127.0.0.1:4001/ui/`. Вход в UI: `admin` и значение `LITELLM_MASTER_KEY`.

## Проверки

Статическая проверка и регрессии совместимости не обращаются к моделям:

```bash
./validate-repo.sh
./test-offline.sh
```

`test-offline.sh` запускает проверки преобразования Responses/tool history в закреплённом образе Docker без сети и без чтения `.env`. Интеграционные тесты Яндекса запускают настоящий шлюз против локальной имитации API без внешней сети. GitHub Actions выполняет только эти проверки и не получает runtime-ключи.

Следующие smoke-тесты вызывают выбранные модели. По умолчанию облачные скрипты используют NVIDIA; они не запускают обход Cloud.ru. Не подставляйте Cloud.ru ID в `CODEX_TEST_MODEL` без согласования расходов.

```bash
./test-models.sh
./test-responses.sh
./test-local-models.sh --catalog ollama
./test-local-models.sh local/ollama
./test-multimodal.sh
# Необязательная проверка нестабильных видео/аудио NVIDIA:
TEST_OMNI_MEDIA=1 ./test-multimodal.sh
```

Каталог локальных моделей можно проверить без загрузки каждой модели. Полные локальные тесты запускайте только для установленного и работающего провайдера. Скрипты возвращают ненулевой код при провале проверки.

## Клиенты и перенос

- [CLIENTS_RU.md](CLIENTS_RU.md) — Codex, Claude Code и OpenCode;
- [CURL_EXAMPLES.md](CURL_EXAMPLES.md) — примеры Chat, Responses, tools и медиа;
- [LOCAL_MODELS_RU.md](LOCAL_MODELS_RU.md) — Ollama и LM Studio;
- [YANDEX_RU.md](YANDEX_RU.md) — Яндекс AI Studio и ограниченные платные проверки;
- [DEPLOYMENT_RU.md](DEPLOYMENT_RU.md) — развёртывание на другом хосте;
- [client-configs/](client-configs/) — шаблоны без секретов.

`cloudru_compat.py` исправляет порядок assistant text/reasoning и tool calls в историях Codex при преобразовании Responses в Chat Completions. Он сохраняет содержимое, идентификаторы и результаты инструментов, не перемещая их через границы пользовательских сообщений. Hook применяется только к маршрутам Cloud.ru.

## Модели Яндекса в меню Codex

```bash
mkdir -p ~/.codex/model-catalogs
cp client-configs/codex-yandex.models.json ~/.codex/model-catalogs/yandex-models.json
cp client-configs/codex-yandex.config.toml ~/.codex/yandex.config.toml
# Экспортируйте LITELLM_MASTER_KEY — ключ шлюза, не API-ключ Яндекса.
codex --profile yandex
```

По умолчанию выбран `yandex/chat` — AliceAI LLM Flash. Команда `/model` показывает 12 текстовых моделей. Список маршрутов и переменных находится в [YANDEX_RU.md](YANDEX_RU.md#текстовые-модели). На настроенном хосте запускатель `codex-yandex` сам читает ключ локального LiteLLM. Для Cloud.ru есть отдельный профиль `cloudru-gateway`: установка описана в [CLIENTS_RU.md](CLIENTS_RU.md#cloudru-через-тот-же-шлюз).

## Как добавить модель Яндекса или Cloud.ru

Инструкция подходит для ещё одной публичной модели, дообученной модели или собственного развёртывания с OpenAI-совместимым API. Нужны точный model ID/URI, API base URL с `/v1` и поддерживаемый endpoint-ом Bearer-ключ. Эти значения берите из карточки вашего развёртывания. Для API с другой схемой запросов или аутентификации используйте соответствующий адаптер LiteLLM; название облака само по себе не делает API OpenAI-совместимым.

На каждом шаге редактируйте файлы **каталога, из которого запущен Compose**. На текущем хосте это `/home/runemal/litellm`; копия проекта на внешнем диске и `to_git` используются для публикации и сами по себе рабочий контейнер не обновляют.

### 1. Сохраните приватные параметры в `.env`

Для модели Яндекса на общем endpoint-е достаточно новой переменной модели. Значение включает префикс LiteLLM `openai/` и полный URI из консоли; URI дообученной модели не нужно конструировать по имени обычной модели:

```dotenv
YANDEX_MY_MODEL=openai/replace-with-full-model-uri-from-console
```

Сохраняйте существующие `YANDEX_API_KEY`, `YANDEX_API_BASE` и `YANDEX_FOLDER_ID`. Hook использует один общий ID каталога и добавляет `OpenAI-Project`. Для модели из другого каталога используйте отдельный экземпляр шлюза с соответствующим folder ID.

Для собственного Cloud.ru endpoint-а задайте отдельные параметры. Значения ниже — заглушки, а не формат конкретного сервиса:

```dotenv
CLOUDRU_MY_MODEL=openai/replace-with-model-id-from-deployment
CLOUDRU_CUSTOM_API_BASE=https://replace-with-deployment-host/v1
CLOUDRU_CUSTOM_API_KEY=replace-with-endpoint-bearer-key
```

Для публичной модели Cloud.ru можно сохранить существующие `CLOUDRU_API_BASE` и `CLOUDRU_API_KEY`. Model ID передавайте с регистром и версией из консоли. `.env` остаётся локальным с правами 600; в `.env.example` добавляйте только заглушки.

### 2. Передайте новые переменные контейнеру

Одного добавления в `.env` недостаточно. В `docker-compose.yml`, внутри `services.litellm.environment`, добавьте необходимые записи, сохранив существующие:

```yaml
YANDEX_MY_MODEL: ${YANDEX_MY_MODEL:-openai/replace-with-model-uri}
CLOUDRU_MY_MODEL: ${CLOUDRU_MY_MODEL:-openai/replace-with-model-id}
CLOUDRU_CUSTOM_API_BASE: ${CLOUDRU_CUSTOM_API_BASE:-https://replace-with-deployment-host/v1}
CLOUDRU_CUSTOM_API_KEY: ${CLOUDRU_CUSTOM_API_KEY:-not-configured}
```

Добавляйте переменные только для выбранного примера. Если Яндексу нужен отдельный совместимый endpoint или ключ, используйте `YANDEX_CUSTOM_API_BASE` / `YANDEX_CUSTOM_API_KEY` аналогично и сошлитесь на них в маршруте.

### 3. Добавьте явный маршрут в `litellm_config.yaml`

В массив `model_list` добавьте один из примеров:

```yaml
- model_name: yandex/my-model
  litellm_params:
    model: os.environ/YANDEX_MY_MODEL
    api_key: os.environ/YANDEX_API_KEY
    api_base: os.environ/YANDEX_API_BASE
    use_chat_completions_api: true
    max_retries: 0
    timeout: 60
  model_info:
    mode: chat

- model_name: cloudru/my-model
  litellm_params:
    model: os.environ/CLOUDRU_MY_MODEL
    api_key: os.environ/CLOUDRU_CUSTOM_API_KEY
    api_base: os.environ/CLOUDRU_CUSTOM_API_BASE
    use_chat_completions_api: true
    max_retries: 0
    timeout: 60
  model_info:
    mode: chat
```

`model_name` — имя, которое выбирает клиент. `litellm_params.model` — модель провайдера через переменную окружения. Для собственных моделей сохраняйте префикс `yandex/` или `cloudru/`, а переменные модели называйте `YANDEX_*_MODEL` / `CLOUDRU_*_MODEL`. Валидатор принимает такие явные маршруты без правки Python и без добавления частного ID в снимок публичного каталога. Новые параметры должны присутствовать в Compose. Автоматические переходы в платные провайдеры из `nim/*` запрещены.

Для embeddings используйте `model_info.mode: embedding`, уберите `use_chat_completions_api` и вызывайте `/v1/embeddings`; embedding-модели не добавляются в меню Codex. Tools и качество работы агента зависят от конкретной модели. `use_chat_completions_api` включает мост LiteLLM Responses → Chat и не добавляет отсутствующие у модели возможности.

### 4. Добавьте модель в каталог Codex

Скопируйте **целый объект** из массива `models` соответствующего файла:

- Яндекс: `client-configs/codex-yandex.models.json` → `~/.codex/model-catalogs/yandex-models.json`;
- Cloud.ru: `client-configs/codex-cloudru.models.json` → `~/.codex/model-catalogs/cloudru-models.json`.

В копии измените `slug` на имя нового маршрута (`yandex/my-model` или `cloudru/my-model`), `display_name`, `description` и `priority`. Остальные поля сохраните: Codex нужны метаданные и инструкции модели, которых нет в обычном `/v1/models`. Не отмечайте tools, изображения или reasoning как поддерживаемые без подтверждения. Клиентский контекст не должен превышать контекст развёртывания; общий предел профиля задан в `*.config.toml`.

`model_catalog_json` в `~/.codex/yandex.config.toml` или `~/.codex/cloudru-gateway.config.toml` задаёт путь к каталогу. Параметр `model` задаёт модель по умолчанию; для разового выбора используйте `--model yandex/my-model` или меню `/model`. Добавление в JSON само по себе не создаёт маршрут на шлюзе.

### 5. Проверьте и примените конфигурацию

В проекте запускайте проверки без расходов:

```bash
./validate-repo.sh
./test-offline.sh
```

В каталоге работающего Compose примените изменённые файлы только к шлюзу:

```bash
docker compose config --quiet
docker compose up -d --no-deps --force-recreate --pull never litellm
```

Перезапустите Codex с выбранным профилем. Проверка `/health/liveliness` и чтение `/v1/models` подтверждают загрузку маршрутов, но не inference. Первый пользовательский запрос к облачной модели может тарифицироваться; отключите повторы также в клиенте. В подготовленных профилях Codex HTTP/SSE-повторы уже обнулены.

### 6. Сохраните переносимую конфигурацию

Перенесите изменения YAML, Compose, клиентского JSON и **заглушки** `.env.example` в проект и `to_git`, затем снова выполните статическую проверку. Настоящие ключи, приватные endpoint/model IDs и `.env` в репозиторий не переносите. Снимки `catalogs/*-catalog.json` остаются результатами публичного обнаружения, а не списком частных развёртываний.

## Обновление и безопасность

После изменения `.env` пересоздайте только сервис шлюза:

```bash
docker compose up -d --force-recreate litellm
docker compose logs --tail=100 litellm
```

`docker compose down` сохраняет PostgreSQL volume; `down -v` удаляет данные. Ключи хранятся в `.env` или внешнем окружении. YAML и клиентские шаблоны содержат только ссылки на переменные. `.env`, приватные регистрационные файлы, логи и резервные копии исключены из публикации. Для внешнего доступа используйте HTTPS reverse proxy и ограничьте доступ к портам локальных провайдеров.
