#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

for command_name in bash docker python3; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "Не найдена обязательная команда: $command_name" >&2
    exit 2
  fi
done

bash -n \
  test-models.sh \
  test-local-models.sh \
  test-multimodal.sh \
  test-responses.sh \
  validate-repo.sh

python3 -c '
import json
import os
import pathlib
import re
import tomllib

for path in (
    "client-configs/claude-nim.settings.json",
    "client-configs/opencode-nim.json",
):
    with open(path, encoding="utf-8") as file:
        json.load(file)

for path in (
    "client-configs/codex-nim.config.toml",
    "client-configs/codex-ollama.config.toml",
    "client-configs/codex-lmstudio.config.toml",
):
    tomllib.loads(pathlib.Path(path).read_text(encoding="utf-8"))

required_files = (
    ".env.example",
    "docker-compose.yml",
    "litellm_config.yaml",
    "DEPLOYMENT_RU.md",
    "LOCAL_MODELS_RU.md",
)
for path in required_files:
    if not pathlib.Path(path).is_file():
        raise SystemExit(f"Отсутствует обязательный файл: {path}")

litellm_config = pathlib.Path("litellm_config.yaml").read_text(encoding="utf-8")
for required_fragment in (
    "model_name: ollama/*",
    "model: ollama_chat/*",
    "model_name: lmstudio/*",
    "model: openai/*",
    "check_provider_endpoint: true",
):
    if required_fragment not in litellm_config:
        raise SystemExit(f"В litellm_config.yaml отсутствует: {required_fragment}")

for path in pathlib.Path(".").glob("*.sh"):
    if not os.access(path, os.X_OK):
        raise SystemExit(f"Shell-скрипт не исполняемый: {path}")

for document in pathlib.Path(".").glob("*.md"):
    content = document.read_text(encoding="utf-8")
    for target in re.findall(r"\[[^]]+\]\(([^)]+)\)", content):
        if target.startswith(("http://", "https://", "#")):
            continue
        relative_target = target.split("#", 1)[0]
        if relative_target and not (document.parent / relative_target).exists():
            raise SystemExit(f"Битая ссылка в {document}: {target}")

gitignore = pathlib.Path(".gitignore").read_text(encoding="utf-8").splitlines()
if ".env" not in gitignore or "!.env.example" not in gitignore:
    raise SystemExit(".gitignore должен исключать .env и сохранять .env.example")
print("JSON/TOML: OK")
'

POSTGRES_PASSWORD=validation-password \
NVIDIA_NIM_API_KEY=nvapi-validation \
LITELLM_MASTER_KEY=sk-validation \
LM_STUDIO_MODEL=openai/validation-model \
docker compose config --quiet

echo "Shell и Docker Compose: OK"
echo "Статическая проверка репозитория пройдена."
