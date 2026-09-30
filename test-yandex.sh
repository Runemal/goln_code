#!/usr/bin/env bash
# Four inference requests against ONE explicitly selected Yandex chat route.
set -uo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
MODEL="${1:-yandex/chat}"
if [[ ${YANDEX_TEST_ALLOW_INFERENCE:-0} != 1 ]]; then
  echo "Платные проверки отключены. После согласования расходов задайте YANDEX_TEST_ALLOW_INFERENCE=1." >&2
  exit 2
fi
if (( $# > 1 )) || [[ $MODEL != yandex/chat && $MODEL != yandex/lite ]]; then
  echo "Укажите ровно один маршрут: yandex/chat или yandex/lite." >&2
  exit 2
fi
MAX_OUTPUT="${YANDEX_TEST_MAX_OUTPUT_TOKENS:-128}"
if [[ ! $MAX_OUTPUT =~ ^[1-9][0-9]*$ ]] || (( MAX_OUTPUT > 256 )); then
  echo "YANDEX_TEST_MAX_OUTPUT_TOKENS должен быть от 1 до 256." >&2
  exit 2
fi
readonly MODEL MAX_OUTPUT
ENV_FILE="${ENV_FILE:-$SCRIPT_DIR/.env}"
if [[ -f $ENV_FILE ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi
: "${LITELLM_MASTER_KEY:?Укажите мастер-ключ LiteLLM}"
BASE_URL="${BASE_URL:-http://127.0.0.1:${LITELLM_PORT:-4001}}"
REQUEST_TIMEOUT="${REQUEST_TIMEOUT:-60}"
for command_name in curl jq; do
  command -v "$command_name" >/dev/null || exit 2
done
echo "Одна модель: $MODEL; 4 запроса; до $MAX_OUTPUT выходных токенов на запрос; без повторов curl."
payload=$(jq -nc --arg model "$MODEL" --argjson limit "$MAX_OUTPUT" '{
  model: $model, messages: [{role: "user", content: "Reply only: YANDEX_CHAT_OK"}],
  max_tokens: $limit, stream: false
}')
failures=0
if body=$(curl --max-time "$REQUEST_TIMEOUT" -fsS "$BASE_URL/v1/chat/completions" \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" -H "Content-Type: application/json" -d "$payload") && \
  jq -e '(.choices[0].message.content // "") | type == "string" and length > 0' >/dev/null 2>&1 <<<"$body"; then
  echo "Yandex Chat: OK"
else
  echo "Yandex Chat: FAIL" >&2
  failures=$((failures + 1))
fi
if ! ENV_FILE=/dev/null LITELLM_MASTER_KEY="$LITELLM_MASTER_KEY" BASE_URL="$BASE_URL" \
  REQUEST_TIMEOUT="$REQUEST_TIMEOUT" CODEX_TEST_MODEL="$MODEL" RESPONSES_MAX_OUTPUT_TOKENS="$MAX_OUTPUT" \
  "$SCRIPT_DIR/test-responses.sh"; then
  failures=$((failures + 1))
fi
(( failures == 0 ))
