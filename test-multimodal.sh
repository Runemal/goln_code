#!/usr/bin/env bash
set -uo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${ENV_FILE:-$SCRIPT_DIR/.env}"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

for command_name in curl jq base64 magick ffmpeg; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "Не найдена обязательная команда: $command_name" >&2
    exit 2
  fi
done

: "${LITELLM_MASTER_KEY:?Укажите LITELLM_MASTER_KEY или создайте $ENV_FILE}"

BASE_URL="${BASE_URL:-http://127.0.0.1:${LITELLM_PORT:-4001}}"
REQUEST_TIMEOUT="${REQUEST_TIMEOUT:-120}"
TMP_DIR=$(mktemp -d /tmp/litellm-nim-media.XXXXXX)
trap 'rm -rf -- "$TMP_DIR"' EXIT

magick -size 900x320 xc:white -font DejaVu-Sans -pointsize 54 \
  -fill black -gravity center \
  -annotate +0+0 $'INVOICE 42\nTOTAL: 123.45 USD' \
  "$TMP_DIR/ocr.png"

ffmpeg -hide_banner -loglevel error \
  -f lavfi -i 'color=c=blue:s=320x240:d=1' \
  -vf "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVu-Sans.ttf:text='BLUE VIDEO 7':fontcolor=white:fontsize=32:x=(w-text_w)/2:y=(h-text_h)/2" \
  -c:v libx264 -pix_fmt yuv420p -t 1 -y "$TMP_DIR/video.mp4"

ffmpeg -hide_banner -loglevel error \
  -f lavfi -i 'sine=frequency=440:duration=1' \
  -ar 16000 -ac 1 -c:a pcm_s16le -y "$TMP_DIR/audio.wav"

failures=0

request_media() {
  local model=$1
  local kind=$2
  local path=$3
  local prompt=$4
  local mime data_url payload response curl_status meta body http_status elapsed result

  case "$kind" in
    image) mime=image/png ;;
    video) mime=video/mp4 ;;
    audio) mime=audio/wav ;;
    *) echo "Неподдерживаемый тип медиа: $kind" >&2; return 2 ;;
  esac

  data_url="data:$mime;base64,$(base64 -w0 "$path")"

  if [[ $prompt == __IMAGE_ONLY__ ]]; then
    payload=$(jq -nc --arg model "$model" --arg data "$data_url" '{
      model: $model,
      messages: [{role: "user", content: [
        {type: "image_url", image_url: {url: $data}}
      ]}],
      max_tokens: 512,
      temperature: 0,
      stream: false
    }')
  else
    case "$kind" in
      image)
        payload=$(jq -nc --arg model "$model" --arg data "$data_url" --arg prompt "$prompt" '{
          model: $model,
          messages: [{role: "user", content: [
            {type: "image_url", image_url: {url: $data}},
            {type: "text", text: $prompt}
          ]}],
          max_tokens: 256,
          temperature: 0,
          stream: false
        }')
        ;;
      video)
        payload=$(jq -nc --arg model "$model" --arg data "$data_url" --arg prompt "$prompt" '{
          model: $model,
          messages: [{role: "user", content: [
            {type: "video_url", video_url: {url: $data}},
            {type: "text", text: $prompt}
          ]}],
          max_tokens: 256,
          temperature: 0,
          stream: false
        }')
        ;;
      audio)
        payload=$(jq -nc --arg model "$model" --arg data "$data_url" --arg prompt "$prompt" '{
          model: $model,
          messages: [{role: "user", content: [
            {type: "audio_url", audio_url: {url: $data}},
            {type: "text", text: $prompt}
          ]}],
          max_tokens: 256,
          temperature: 0,
          stream: false
        }')
        ;;
    esac
  fi

  response=$(curl --max-time "$REQUEST_TIMEOUT" -sS \
    -w $'\n__META__%{http_code}\t%{time_total}' \
    "$BASE_URL/v1/chat/completions" \
    -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
    -H "Content-Type: application/json" \
    -d "$payload")
  curl_status=$?

  meta=${response##*$'\n'__META__}
  body=${response%$'\n'__META__*}
  http_status=${meta%%$'\t'*}
  elapsed=${meta#*$'\t'}

  if [[ $curl_status -eq 0 && $http_status == 200 ]] && jq -e '.choices[0]' >/dev/null 2>&1 <<<"$body"; then
    result=$(jq -r '
      .choices[0].message.content
      // .choices[0].message.tool_calls[0].function.arguments
      // .choices[0].message.reasoning_content
      // "ответ получен"
    ' <<<"$body")
    result=${result//$'\n'/ }
    printf '%-24s %-7s %-8s %.100s\n' "$model" "OK" "$elapsed" "$result"
  else
    result=$(jq -r '.error.message // .detail // "ошибка запроса"' <<<"$body" 2>/dev/null || echo "ошибка запроса")
    result=${result//$'\n'/ }
    printf '%-24s %-7s %-8s HTTP %s: %.100s\n' "$model" "FAIL" "$elapsed" "$http_status" "$result"
    failures=$((failures + 1))
  fi
}

echo "Мультимодальный тест LiteLLM: $BASE_URL"
printf '%-24s %-7s %-8s %s\n' "МОДЕЛЬ" "СТАТУС" "СЕКУНДЫ" "РЕЗУЛЬТАТ"
printf '%s\n' "------------------------------------------------------------------------------------------------"

request_media "nim/vision" image "$TMP_DIR/ocr.png" "Прочитай весь видимый текст."
request_media "nim/ocr" image "$TMP_DIR/ocr.png" "Извлеки весь текст без изменений."
request_media "nim/ocr-structured" image "$TMP_DIR/ocr.png" "__IMAGE_ONLY__"
request_media "nim/omni" video "$TMP_DIR/video.mp4" "Опиши видео и прочитай видимый текст."
request_media "nim/omni" audio "$TMP_DIR/audio.wav" "Опиши аудио: это речь, музыка или тон?"

if [[ $failures -eq 0 ]]; then
  echo "Все мультимодальные проверки пройдены."
  exit 0
fi

echo "Не пройдено мультимодальных проверок: $failures." >&2
exit 1
