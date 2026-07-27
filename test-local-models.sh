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

BASE_URL="${BASE_URL:-http://127.0.0.1:${LITELLM_PORT:-4001}}"
REQUEST_TIMEOUT="${REQUEST_TIMEOUT:-300}"

usage() {
  cat <<'EOF'
Использование:
  ./test-local-models.sh                         # стабильные local/* алиасы
  ./test-local-models.sh local/ollama MODEL...   # указанные модели
  ./test-local-models.sh --catalog               # каталоги Ollama и LM Studio
  ./test-local-models.sh --catalog ollama        # только один каталог
EOF
}

if [[ ${1:-} == --help || ${1:-} == -h ]]; then
  usage
  exit 0
fi

: "${LITELLM_MASTER_KEY:?Укажите LITELLM_MASTER_KEY или создайте $ENV_FILE}"

catalog_mode=false
if [[ ${1:-} == --catalog ]]; then
  catalog_mode=true
  shift
fi

if ! curl --max-time 10 -fsS "$BASE_URL/health/liveliness" >/dev/null; then
  echo "ОШИБКА: LiteLLM недоступен по адресу $BASE_URL" >&2
  exit 1
fi

if [[ $catalog_mode == true ]]; then
  if (( $# > 0 )); then
    CATALOG_PREFIXES=("$@")
  else
    CATALOG_PREFIXES=(ollama lmstudio)
  fi

  if ! catalog_body=$(curl --max-time "$REQUEST_TIMEOUT" -fsS \
    "$BASE_URL/v1/models" \
    -H "Authorization: Bearer $LITELLM_MASTER_KEY"); then
    echo "ОШИБКА: не удалось получить динамический каталог LiteLLM" >&2
    exit 1
  fi

  failures=0
  for catalog_prefix in "${CATALOG_PREFIXES[@]}"; do
    catalog_prefix="${catalog_prefix%/}/"
    mapfile -t catalog_models < <(
      jq -r --arg prefix "$catalog_prefix" \
        '.data[]?.id | select(startswith($prefix) and . != ($prefix + "*"))' \
        <<<"$catalog_body" | sort -u
    )

    if (( ${#catalog_models[@]} == 0 )); then
      echo "${catalog_prefix%/}: модели не обнаружены" >&2
      failures=$((failures + 1))
      continue
    fi

    printf '%s: %d моделей\n' "${catalog_prefix%/}" "${#catalog_models[@]}"
    printf '  %s\n' "${catalog_models[@]}"
  done

  if (( failures == 0 )); then
    echo "Динамический каталог локальных моделей доступен."
    exit 0
  fi

  echo "Не обнаружено локальных каталогов: $failures." >&2
  exit 1
fi

if (( $# > 0 )); then
  MODELS=("$@")
else
  read -r -a MODELS <<<"${LOCAL_TEST_MODELS:-local/ollama local/lmstudio}"
fi

if (( ${#MODELS[@]} == 0 )); then
  echo "Не указаны локальные модели для проверки" >&2
  exit 2
fi

failures=0
printf '%-24s %-12s %-12s %-12s\n' "МОДЕЛЬ" "CHAT" "RESPONSES" "TOOLS"
printf '%s\n' "------------------------------------------------------------------------"

for model in "${MODELS[@]}"; do
  chat_status=FAIL
  responses_status=FAIL
  tools_status=FAIL

  payload=$(jq -nc --arg model "$model" '{
    model: $model,
    messages: [{role: "user", content: "Ответь только: LOCAL_CHAT_OK"}],
    max_tokens: 128,
    temperature: 0
  }')
  body=$(curl --max-time "$REQUEST_TIMEOUT" -sS "$BASE_URL/v1/chat/completions" \
    -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
    -H "Content-Type: application/json" \
    -d "$payload")
  curl_status=$?
  if [[ $curl_status -eq 0 ]] && jq -e '.choices[0].message' >/dev/null 2>&1 <<<"$body"; then
    chat_status=OK
  else
    failures=$((failures + 1))
    jq -r '.error.message // .detail // "ошибка chat/completions"' <<<"$body" >&2 2>/dev/null || true
  fi

  payload=$(jq -nc --arg model "$model" '{
    model: $model,
    input: "Ответь только: LOCAL_RESPONSES_OK",
    max_output_tokens: 256,
    client_metadata: {source: "local-model-smoke-test"}
  }')
  body=$(curl --max-time "$REQUEST_TIMEOUT" -sS "$BASE_URL/v1/responses" \
    -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
    -H "Content-Type: application/json" \
    -d "$payload")
  curl_status=$?
  if [[ $curl_status -eq 0 ]] && jq -e '.status == "completed"' >/dev/null 2>&1 <<<"$body"; then
    responses_status=OK
  else
    failures=$((failures + 1))
    jq -r '.error.message // .detail // ("Responses status: " + (.status // "unknown"))' <<<"$body" >&2 2>/dev/null || true
  fi

  payload=$(jq -nc --arg model "$model" '{
    model: $model,
    messages: [{role: "user", content: "Обязательно вызови local_probe со значением test."}],
    tools: [{
      type: "function",
      function: {
        name: "local_probe",
        description: "Проверка передачи инструментов",
        parameters: {
          type: "object",
          properties: {value: {type: "string"}},
          required: ["value"]
        }
      }
    }],
    tool_choice: "auto",
    max_tokens: 256,
    temperature: 0
  }')
  body=$(curl --max-time "$REQUEST_TIMEOUT" -sS "$BASE_URL/v1/chat/completions" \
    -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
    -H "Content-Type: application/json" \
    -d "$payload")
  curl_status=$?
  tool_name=$(jq -r '.choices[0].message.tool_calls[0].function.name // ""' <<<"$body" 2>/dev/null)
  if [[ $curl_status -eq 0 && $tool_name == local_probe ]]; then
    tools_status=OK
  else
    failures=$((failures + 1))
    jq -r '.error.message // .detail // .choices[0].message.content // "вызов инструмента отсутствует"' <<<"$body" >&2 2>/dev/null || true
  fi

  printf '%-24s %-12s %-12s %-12s\n' "$model" "$chat_status" "$responses_status" "$tools_status"
done

if [[ $failures -eq 0 ]]; then
  echo "Все проверки локальных моделей пройдены."
  exit 0
fi

echo "Не пройдено локальных проверок: $failures." >&2
exit 1
