#!/usr/bin/env bash

# 前端启动脚本
# 功能：
# 1) 检查并释放端口占用（默认3000）
# 2) 激活 conda 环境 make_image
# 3) 启动前端开发服务器（npm run dev）
# 4) 将启动日志写入指定日志文件
# 5) 错误处理与明确的控制台输出

set -euo pipefail

DEFAULT_PORT=3000
PORT="${1:-$DEFAULT_PORT}"
LOG_DIR="${LOG_DIR:-logs}"
TS="$(date +'%Y%m%d_%H%M%S')"
LOG_FILE="${LOG_DIR}/frontend_${TS}.log"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

function info() { echo "[INFO] $*"; }
function warn() { echo "[WARN] $*" >&2; }
function err()  { echo "[ERROR] $*" >&2; }

# 创建日志目录
mkdir -p "$LOG_DIR" || { err "无法创建日志目录: $LOG_DIR"; exit 1; }

info "目标端口: ${PORT}"

# 端口占用检测与释放
function free_port() {
  local p="$1"
  if command -v fuser >/dev/null 2>&1; then
    if fuser "${p}/tcp" >/dev/null 2>&1; then
      warn "端口 ${p} 被占用，尝试释放..."
      if ! fuser -k "${p}/tcp"; then
        err "释放端口 ${p} 失败"
        return 1
      fi
      info "已释放端口 ${p}"
    fi
  elif command -v lsof >/dev/null 2>&1; then
    local pids
    pids="$(lsof -t -iTCP -sTCP:LISTEN -P -n ":${p}" || true)"
    if [[ -n "$pids" ]]; then
      warn "端口 ${p} 被占用，尝试终止进程: ${pids}"
      if ! kill -9 $pids; then
        err "终止端口 ${p} 进程失败"
        return 1
      fi
      info "已终止占用端口的进程: ${pids}"
    fi
  else
    err "未找到端口检测工具 (fuser/lsof)"
    return 1
  fi
  return 0
}

free_port "$PORT" || warn "端口释放可能失败，继续尝试启动"

info "等待5秒以确保资源释放..."
sleep 5

# 激活 conda 环境
if command -v conda >/dev/null 2>&1; then
  eval "$(conda shell.bash hook)" || { err "初始化 conda shell 失败"; exit 1; }
  conda activate make_image || { err "激活 conda 环境失败: make_image"; exit 1; }
else
  err "未检测到 conda，请先安装并配置"
  exit 1
fi

info "启动前端服务 (npm run dev) ..."
set +e
nohup npm run dev -- --host 0.0.0.0 --port "${PORT}" >> "${LOG_FILE}" 2>&1 &
PID=$!
set -e

if ps -p "${PID}" >/dev/null 2>&1; then
  info "前端已启动，PID=${PID}，日志: ${LOG_FILE}"
  exit 0
else
  err "前端启动失败，请查看日志: ${LOG_FILE}"
  exit 2
fi

