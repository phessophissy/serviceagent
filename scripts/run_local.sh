#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -d ".venv" ]]; then
  python3 -m venv .venv
fi

source .venv/bin/activate

if [[ -f ".env" ]]; then
  set -a
  # shellcheck source=/dev/null
  source .env
  set +a
fi

export PYTHONPATH="$ROOT_DIR"

python backend/scripts/bootstrap_aws_resources.py
uvicorn backend.src.api.lambda_app:app --host 0.0.0.0 --port "${PORT:-8000}" --reload
