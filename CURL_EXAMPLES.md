# Примеры curl-запросов

Все команды используют OpenAI-совместимый адрес LiteLLM:

```bash
export LITELLM_URL=http://127.0.0.1:4001
export LITELLM_MASTER_KEY=sk-ваш-мастер-ключ
```

## Список моделей

```bash
curl -fsS "$LITELLM_URL/v1/models" \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" | jq
```

Только динамические локальные каталоги:

```bash
curl -fsS "$LITELLM_URL/v1/models" \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" |
jq -r '.data[].id | select(startswith("ollama/") or startswith("lmstudio/"))'
```

## Быстрый текстовый запрос

```bash
curl -fsS "$LITELLM_URL/v1/chat/completions" \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "nim/fast",
    "messages": [
      {"role": "user", "content": "Объясни NVIDIA NIM двумя предложениями."}
    ],
    "max_tokens": 256,
    "temperature": 0.3
  }' | jq
```

## Вызов инструмента

```bash
curl -fsS "$LITELLM_URL/v1/chat/completions" \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "nim/agent",
    "messages": [
      {"role": "user", "content": "Какая погода в Москве? Используй инструмент."}
    ],
    "tools": [{
      "type": "function",
      "function": {
        "name": "get_weather",
        "description": "Получить погоду для города",
        "parameters": {
          "type": "object",
          "properties": {
            "city": {"type": "string"}
          },
          "required": ["city"]
        }
      }
    }],
    "tool_choice": "auto",
    "max_tokens": 256
  }' | jq
```

Результат вызова находится в:

```text
choices[0].message.tool_calls
```

## Анализ изображения

```bash
IMAGE_DATA=$(base64 -w0 image.png)

jq -nc \
  --arg image "data:image/png;base64,$IMAGE_DATA" \
  '{
    model: "nim/vision",
    messages: [{
      role: "user",
      content: [
        {type: "image_url", image_url: {url: $image}},
        {type: "text", text: "Подробно опиши изображение."}
      ]
    }],
    max_tokens: 512
  }' |
curl -fsS "$LITELLM_URL/v1/chat/completions" \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d @- | jq
```

## Обычный OCR

```bash
IMAGE_DATA=$(base64 -w0 document.png)

jq -nc \
  --arg image "data:image/png;base64,$IMAGE_DATA" \
  '{
    model: "nim/ocr",
    messages: [{
      role: "user",
      content: [
        {type: "image_url", image_url: {url: $image}},
        {type: "text", text: "Извлеки весь текст без изменений."}
      ]
    }],
    max_tokens: 1024
  }' |
curl -fsS "$LITELLM_URL/v1/chat/completions" \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d @- | jq
```

## Структурированный OCR с bbox

Для `nim/ocr-structured` передавайте только изображение, без текстовой части:

```bash
IMAGE_DATA=$(base64 -w0 document.png)

jq -nc \
  --arg image "data:image/png;base64,$IMAGE_DATA" \
  '{
    model: "nim/ocr-structured",
    messages: [{
      role: "user",
      content: [
        {type: "image_url", image_url: {url: $image}}
      ]
    }],
    max_tokens: 2048
  }' |
curl -fsS "$LITELLM_URL/v1/chat/completions" \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d @- | jq
```

Текст и координаты находятся в:

```text
choices[0].message.tool_calls[0].function.arguments
```

## Анализ видео

```bash
VIDEO_DATA=$(base64 -w0 video.mp4)

jq -nc \
  --arg video "data:video/mp4;base64,$VIDEO_DATA" \
  '{
    model: "nim/omni",
    messages: [{
      role: "user",
      content: [
        {type: "video_url", video_url: {url: $video}},
        {type: "text", text: "Опиши происходящее в видео."}
      ]
    }],
    max_tokens: 512
  }' |
curl -fsS "$LITELLM_URL/v1/chat/completions" \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d @- | jq
```

## Анализ аудио

```bash
AUDIO_DATA=$(base64 -w0 audio.wav)

jq -nc \
  --arg audio "data:audio/wav;base64,$AUDIO_DATA" \
  '{
    model: "nim/omni",
    messages: [{
      role: "user",
      content: [
        {type: "audio_url", audio_url: {url: $audio}},
        {type: "text", text: "Опиши содержимое аудиозаписи."}
      ]
    }],
    max_tokens: 512
  }' |
curl -fsS "$LITELLM_URL/v1/chat/completions" \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d @- | jq
```

Большие файлы лучше передавать по доступному NVIDIA HTTPS URL, если конкретная модель поддерживает удалённые media URL: base64 увеличивает размер запроса примерно на треть.

## Локальная Ollama-модель

Стабильный алиас использует `OLLAMA_MODEL` из `.env`. Для конкретной установленной модели замените значение `model` на маршрут вида `ollama/gemma3:12b`.

```bash
curl -fsS "$LITELLM_URL/v1/chat/completions" \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "local/ollama",
    "messages": [{"role": "user", "content": "Ответь только: OLLAMA_OK"}],
    "max_tokens": 128
  }' | jq
```

## Локальная LM Studio-модель

Стабильный алиас использует `LM_STUDIO_MODEL` из `.env`. Конкретную опубликованную модель можно вызвать как `lmstudio/granite-4.0-h-tiny`.

```bash
curl -fsS "$LITELLM_URL/v1/responses" \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "local/lmstudio",
    "input": "Ответь только: LM_STUDIO_OK",
    "max_output_tokens": 256
  }' | jq
```
