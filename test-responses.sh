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
MODEL="${CODEX_TEST_MODEL:-nim/agent}"
REQUEST_TIMEOUT="${REQUEST_TIMEOUT:-120}"
MAX_OUTPUT_TOKENS="${RESPONSES_MAX_OUTPUT_TOKENS:-256}"
failures=0

if [[ ! $MAX_OUTPUT_TOKENS =~ ^[1-9][0-9]*$ ]]; then
  echo "RESPONSES_MAX_OUTPUT_TOKENS должен быть положительным целым числом" >&2
  exit 2
fi

request_json=$(jq -nc --arg model "$MODEL" --argjson max_output_tokens "$MAX_OUTPUT_TOKENS" '{
  model: $model,
  input: "Ответь только: RESPONSES_OK",
  max_output_tokens: $max_output_tokens,
  client_metadata: {source: "codex-regression-test"}
}')

response=$(curl --max-time "$REQUEST_TIMEOUT" -sS \
  -w $'\n__META__%{http_code}\t%{time_total}' \
  "$BASE_URL/v1/responses" \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d "$request_json")
curl_status=$?
meta=${response##*$'\n'__META__}
body=${response%$'\n'__META__*}
http_status=${meta%%$'\t'*}
elapsed=${meta#*$'\t'}

if [[ $curl_status -eq 0 && $http_status == 200 ]] && jq -e '.id and .status == "completed"' >/dev/null 2>&1 <<<"$body"; then
  echo "Responses API: OK (${elapsed} с)"
else
  error=$(jq -r '.error.message // .detail // "ошибка запроса"' <<<"$body" 2>/dev/null || echo "ошибка запроса")
  echo "Responses API: FAIL (HTTP $http_status): $error" >&2
  failures=$((failures + 1))
fi

stream_json=$(jq -nc --arg model "$MODEL" --argjson max_output_tokens "$MAX_OUTPUT_TOKENS" '{
  model: $model,
  input: "Ответь только: STREAM_OK",
  max_output_tokens: $max_output_tokens,
  stream: true,
  client_metadata: {source: "codex-stream-regression-test"}
}')

stream_response=$(curl --max-time "$REQUEST_TIMEOUT" -sS -N \
  -w $'\n__META__%{http_code}\t%{time_total}' \
  "$BASE_URL/v1/responses" \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d "$stream_json")
curl_status=$?
meta=${stream_response##*$'\n'__META__}
stream_body=${stream_response%$'\n'__META__*}
http_status=${meta%%$'\t'*}
elapsed=${meta#*$'\t'}

if [[ $curl_status -eq 0 && $http_status == 200 ]] && grep -q 'response.completed' <<<"$stream_body"; then
  echo "Responses SSE: OK (${elapsed} с)"
else
  echo "Responses SSE: FAIL (HTTP $http_status)" >&2
  failures=$((failures + 1))
fi

tool_json=$(jq -nc --arg model "$MODEL" --argjson max_output_tokens "$MAX_OUTPUT_TOKENS" '{
  model: $model,
  input: "Какая погода в Москве? Обязательно используй инструмент.",
  tools: [{
    type: "function",
    name: "get_weather",
    description: "Получить текущую погоду для города",
    parameters: {
      type: "object",
      properties: {city: {type: "string"}},
      required: ["city"]
    }
  }],
  tool_choice: "required",
  max_output_tokens: $max_output_tokens,
  client_metadata: {source: "codex-tool-regression-test"}
}')

tool_response=$(curl --max-time "$REQUEST_TIMEOUT" -sS \
  -w $'\n__META__%{http_code}\t%{time_total}' \
  "$BASE_URL/v1/responses" \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d "$tool_json")
curl_status=$?
meta=${tool_response##*$'\n'__META__}
tool_body=${tool_response%$'\n'__META__*}
http_status=${meta%%$'\t'*}
elapsed=${meta#*$'\t'}
tool_name=$(jq -r '[.. | objects | select(.type? == "function_call") | .name][0] // ""' <<<"$tool_body" 2>/dev/null)

if [[ $curl_status -eq 0 && $http_status == 200 && $tool_name == get_weather ]]; then
  echo "Responses tools: OK (${elapsed} с)"
else
  error=$(jq -r '.error.message // .detail // "вызов инструмента отсутствует"' <<<"$tool_body" 2>/dev/null || echo "ошибка запроса")
  echo "Responses tools: FAIL (HTTP $http_status): $error" >&2
  failures=$((failures + 1))
fi

if [[ $failures -eq 0 ]]; then
  echo "Все проверки совместимости Codex пройдены для $MODEL."
  exit 0
fi

echo "Не пройдено проверок Responses API: $failures." >&2
exit 1
