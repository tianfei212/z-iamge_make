#!/usr/bin/env bash
set -euo pipefail

function err() { echo "[ERROR] $*" >&2; }
function info() { echo "[INFO] $*"; }

if ! command -v conda >/dev/null 2>&1; then
  err "未检测到 conda，请先安装"
  exit 2
fi
eval "$(conda shell.bash hook)" || { err "初始化 conda 失败"; exit 2; }

ENV_NAME="${CONDA_DEFAULT_ENV:-}"
if [[ -z "$ENV_NAME" ]]; then
  err "未处于任何 conda 环境，请先激活 make_image"
  exit 2
fi
if [[ "$ENV_NAME" != "make_image" ]]; then
  err "当前环境为 '$ENV_NAME'，需要在 'make_image' 环境下运行"
  exit 2
fi
info "当前 conda 环境: $ENV_NAME"

PY_VER="$(python -c 'import sys; print(f\"{sys.version_info.major}.{sys.version_info.minor}\")')"
info "Python 版本: $PY_VER"

function has_pkg() {
  python - "$1" <<'PY'
import importlib, sys
name=sys.argv[1]
try:
  m=importlib.import_module(name)
  print(getattr(m, "__version__", "ok"))
except Exception as e:
  print("")
PY
}

FASTAPI_VER="$(has_pkg fastapi)"
UVICORN_VER="$(has_pkg uvicorn)"
PILLOW_VER="$(has_pkg PIL)"
SQLITE_VER="$(python -c 'import sqlite3; print(sqlite3.sqlite_version)' || true)"

[[ -n "$FASTAPI_VER" ]] || { err "缺少 fastapi"; exit 3; }
[[ -n "$UVICORN_VER" ]] || { err "缺少 uvicorn"; exit 3; }
[[ -n "$PILLOW_VER" ]] || { err "缺少 pillow"; exit 3; }

info "fastapi: ${FASTAPI_VER}"
info "uvicorn: ${UVICORN_VER}"
info "pillow: ${PILLOW_VER}"
info "sqlite: ${SQLITE_VER}"

echo "[OK] 环境检查通过"
exit 0
