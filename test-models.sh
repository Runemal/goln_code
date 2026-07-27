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

for command_name in curl jq; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "Не найдена обязательная команда: $command_name" >&2
    exit 2
  fi
done

: "${LITELLM_MASTER_KEY:?Укажите LITELLM_MASTER_KEY или создайте $ENV_FILE}"

BASE_URL="${BASE_URL:-http://127.0.0.1:${LITELLM_PORT:-4001}}"
REQUEST_TIMEOUT="${REQUEST_TIMEOUT:-120}"

MODELS=(
  "nim/fast"
  "nim/chat"
  "nim/agent"
  "nim/code"
  "nim/reasoning"
)

TOOL_MODELS=(
  "nim/agent"
  "nim/code"
)

echo "Адрес LiteLLM: $BASE_URL"
if ! curl --max-time 10 -fsS "$BASE_URL/health/liveliness" >/dev/null; then
  echo "ОШИБКА: LiteLLM недоступен" >&2
  exit 1
fi
echo "Проверка доступности: OK"

echo "Настроенные модели:"
curl --max-time 10 -fsS "$BASE_URL/v1/models" \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  | jq -r '.data[].id | "  - " + .'

printf "\n%-48s %-8s %-8s %s\n" "МОДЕЛЬ" "СТАТУС" "СЕКУНДЫ" "ОТВЕТ"
printf '%s\n' "------------------------------------------------------------------------------------------------"

failures=0
for model in "${MODELS[@]}"; do
  payload=$(jq -nc --arg model "$model" '{
    model: $model,
    messages: [{role: "user", content: "Ответь ровно одним словом: OK"}],
    max_tokens: 16,
    temperature: 0,
    stream: false
  }')

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

  if [[ $curl_status -eq 0 && $http_status == "200" ]] && jq -e '.choices[0]' >/dev/null 2>&1 <<<"$body"; then
    content=$(jq -r '.choices[0].message.content // .choices[0].message.reasoning_content // ""' <<<"$body" \
      | tr '\n' ' ' \
      | cut -c1-70)
    printf "%-48s %-8s %-8s %s\n" "$model" "OK" "$elapsed" "$content"
  else
    error=$(jq -r '.error.message // .detail // "ошибка запроса"' <<<"$body" 2>/dev/null || echo "ошибка запроса")
    printf "%-48s %-8s %-8s HTTP %s: %s\n" "$model" "FAIL" "$elapsed" "$http_status" "$error"
    failures=$((failures + 1))
  fi
done

printf "\n%-48s %-12s %-8s %s\n" "МОДЕЛЬ" "TOOLS" "СЕКУНДЫ" "РЕЗУЛЬТАТ"
printf '%s\n' "------------------------------------------------------------------------------------------------"

for model in "${TOOL_MODELS[@]}"; do
  payload=$(jq -nc --arg model "$model" '{
    model: $model,
    messages: [{role: "user", content: "Какая погода в Москве? Используй предоставленный инструмент."}],
    tools: [{
      type: "function",
      function: {
        name: "get_weather",
        description: "Получить текущую погоду для города",
        parameters: {
          type: "object",
          properties: {city: {type: "string"}},
          required: ["city"]
        }
      }
    }],
    tool_choice: "auto",
    max_tokens: 128,
    temperature: 0,
    stream: false
  }')

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
  tool_name=$(jq -r '.choices[0].message.tool_calls[0].function.name // ""' <<<"$body" 2>/dev/null)

  if [[ $curl_status -eq 0 && $http_status == "200" && $tool_name == "get_weather" ]]; then
    printf "%-48s %-12s %-8s %s\n" "$model" "OK" "$elapsed" "$tool_name"
  else
    error=$(jq -r '.error.message // .detail // .choices[0].message.content // "вызов инструмента отсутствует"' <<<"$body" 2>/dev/null || echo "ошибка запроса")
    error=${error//$'\n'/ }
    printf "%-48s %-12s %-8s HTTP %s: %s\n" "$model" "FAIL" "$elapsed" "$http_status" "$error"
    failures=$((failures + 1))
  fi
done

printf "\n"
if [[ $failures -eq 0 ]]; then
  echo "Все проверки моделей пройдены."
  exit 0
fi

echo "Не пройдено проверок моделей: $failures." >&2
exit 1
