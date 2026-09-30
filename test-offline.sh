#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
IMAGE="${OFFLINE_TEST_IMAGE:-ghcr.io/berriai/litellm-database@sha256:72360d8bd5602faa49be5098a8ac3dd069d9fb74503d6bd014242d96dc753e43}"
# No runtime .env is sourced. Tests have no network and cannot call providers.
docker run --rm --network none \
  -e PYTHONDONTWRITEBYTECODE=1 -e LITELLM_LOCAL_MODEL_COST_MAP=True \
  -v "$SCRIPT_DIR:/workspace:ro" -w /workspace \
  --entrypoint python "$IMAGE" -m unittest -v test_cloudru_compat test_validate_config
