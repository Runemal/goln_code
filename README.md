# LiteLLM gateway: NVIDIA NIM, Cloud.ru, Ollama и LM Studio

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
| `local/ollama`, `local/lmstudio` | Модель из переменных `OLLAMA_MODEL` / `LM_STUDIO_MODEL` |
| `ollama/*`, `lmstudio/*` | Динамический каталог локального провайдера |

Например, `cloudru/Qwen/Qwen3-Coder-Next` направляется в Cloud.ru, а `ollama/gemma4:12b` — в локальную Ollama. Шесть старых точных Cloud.ru ID сохранены для совместимости существующих клиентов; полный список есть в [MODEL_STATUS.md](MODEL_STATUS.md).

Cloud.ru не входит в алиасы `nim/*` и не используется как запасной провайдер. Автоматические повторы на шлюзе отключены (`num_retries: 0`), чтобы ошибка не запускала дополнительный inference-запрос. Клиентские повторы настраиваются отдельно.

NVIDIA-алиас содержит один или несколько deployments; маршрутизатор выбирает одну модель по измеренной задержке. Полные каталоги находятся в [catalogs/](catalogs/): 81 NVIDIA ID и 95 Cloud.ru ID. Наличие ID в каталоге не подтверждает доступность inference; в YAML включено проверенное подмножество и совместимые старые Cloud.ru маршруты.

## Настройка

Нужны Docker и Compose v2. Для проверок: `curl`, `jq`, Python 3.11+ и PyYAML (`python3 -m pip install PyYAML==6.0.3`). Для мультимодальных тестов дополнительно нужны ImageMagick и ffmpeg. Локальные серверы устанавливаются отдельно.

```bash
cp .env.example .env
chmod 600 .env
```

Замените `LITELLM_MASTER_KEY` и `POSTGRES_PASSWORD`. Для NVIDIA заполните `NVIDIA_NIM_API_KEY`, для Cloud.ru — `CLOUDRU_API_KEY`; неиспользуемые облачные ключи можно оставить заглушками. Укажите реально установленную модель Ollama и/или загруженную модель LM Studio. На проверенном хосте установлены `gemma4:12b` и `qwen3.5:9b-q8_0`, а LM Studio сейчас выключена.

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

`test-offline.sh` запускает проверки преобразования Responses/tool history в закреплённом образе Docker без сети и без чтения `.env`. GitHub Actions выполняет только эти проверки и не получает runtime-ключи.

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
- [DEPLOYMENT_RU.md](DEPLOYMENT_RU.md) — развёртывание на другом хосте;
- [client-configs/](client-configs/) — шаблоны без секретов.

`cloudru_compat.py` исправляет порядок assistant text/reasoning и tool calls в историях Codex при преобразовании Responses в Chat Completions. Он сохраняет содержимое, идентификаторы и результаты инструментов, не перемещая их через границы пользовательских сообщений. Hook применяется только к маршрутам Cloud.ru.

## Обновление и безопасность

После изменения `.env` пересоздайте только сервис шлюза:

```bash
docker compose up -d --force-recreate litellm
docker compose logs --tail=100 litellm
```

`docker compose down` сохраняет PostgreSQL volume; `down -v` удаляет данные. Ключи хранятся в `.env` или внешнем окружении. YAML и клиентские шаблоны содержат только ссылки на переменные. `.env`, приватные регистрационные файлы, логи и резервные копии исключены из публикации. Для внешнего доступа используйте HTTPS reverse proxy и ограничьте доступ к портам локальных провайдеров.
