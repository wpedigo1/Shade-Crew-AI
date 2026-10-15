#!/usr/bin/env bash
# One native llama.cpp router; no model downloads, service or extra manager.
set -euo pipefail
SHADE_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME='/home/wes/runtime/llama.cpp/releases/b11228/llama-server'
[[ -x "$RUNTIME" ]] || { echo "Pinned b11228 runtime is missing: $RUNTIME" >&2; exit 1; }
for model in \
  '/home/wes/models/qwen38-uncensored-27b/Qwen3.8-27B-Uncensored-FP8.Q4_K_M.gguf' \
  '/home/wes/models/qwen36-heretic-35b/Qwen3.6-35B-A3B-uncensored-heretic-Native-MTP-Preserved-Q4_K_M.gguf'; do
  [[ -r "$model" ]] || { echo "Existing model is missing: $model" >&2; exit 1; }
done
exec "$RUNTIME" --models-preset "$SHADE_ROOT/config/fob-models.ini" \
  --models-max 1 --host 127.0.0.1 --port 18081 --no-webui --metrics --log-verbosity 4
