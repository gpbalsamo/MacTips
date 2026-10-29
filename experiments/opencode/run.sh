#!/usr/bin/env bash
# Project-local OpenCode; no shell-profile or global configuration changes.
set -euo pipefail
opencode_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
opencode_repo="$(cd -- "$opencode_dir/../.." && pwd)"
opencode_runtime="$opencode_dir/runtime"
opencode_bin="$opencode_runtime/node_modules/.bin/opencode"
if [[ ! -x "$opencode_bin" ]]; then
    echo 'OpenCode is not installed here. See experiments/opencode/README.md.' >&2
    exit 1
fi
umask 077
export XDG_CONFIG_HOME="$opencode_runtime/config"
export XDG_DATA_HOME="$opencode_runtime/data"
export XDG_CACHE_HOME="$opencode_runtime/cache"
export XDG_STATE_HOME="$opencode_runtime/state"
export OPENCODE_DISABLE_AUTOUPDATE=true
export OPENCODE_DISABLE_MODELS_FETCH=true
export OPENCODE_DISABLE_DEFAULT_PLUGINS=true
export OPENCODE_DISABLE_PROJECT_CONFIG=true
export OPENCODE_CONFIG_CONTENT
OPENCODE_CONFIG_CONTENT="$(cat -- "$opencode_dir/opencode.json")"
mkdir -p -- "$XDG_CONFIG_HOME" "$XDG_DATA_HOME" "$XDG_CACHE_HOME" "$XDG_STATE_HOME"
cd -- "$opencode_repo"
exec "$opencode_bin" --pure "$@"
