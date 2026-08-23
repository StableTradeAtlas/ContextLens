#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
python3 gpu/prepare_corpus.py
python3 -m pip install --disable-pip-version-check -q -r gpu/requirements.txt
RUNPOD_RATE_USD_PER_HOUR="${RUNPOD_RATE_USD_PER_HOUR:-2.10}" python3 gpu/build_embeddings.py
