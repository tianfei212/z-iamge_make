# 启动脚本使用说明

本项目提供两个独立的 Bash 启动脚本，用于一键启动前端与后端服务，并满足端口检测、进程释放、conda 环境激活、日志记录等要求。

## 文件列表
- `start_frontend.sh`：启动前端（默认端口 3000）
- `start_backend.sh`：启动后端（默认端口 8000）

## 前置要求
- 已安装并可用的 Conda，且存在环境 `make_image`
- 已在项目根目录执行脚本（脚本会自动切换到脚本所在目录）
- 前端依赖已安装（npm i）
- 后端 Python 依赖已安装（见 backend/requirements.txt）

## 参数与环境变量
- 端口参数（可选）：
  - 前端：`./start_frontend.sh [PORT]`，默认 `3000`
  - 后端：`./start_backend.sh [PORT]`，默认 `8000`
- 环境变量（可选）：
  - 统一设置日志目录：`LOG_DIR=logs`（默认为 `logs`）
  - 后端设置绑定地址：`HOST=0.0.0.0`（默认为 `0.0.0.0`）

## 日志
- 启动日志会写入 `logs/frontend_YYYYMMDD_HHMMSS.log` 或 `logs/backend_YYYYMMDD_HHMMSS.log`
- 若日志目录不存在，脚本会自动创建

## 功能说明
1. 端口占用检测与释放
   - 使用 `fuser` 或 `lsof` 检测并终止占用该端口的进程
2. 资源释放等待
   - 在终止进程后等待 5 秒，确保系统释放端口和文件句柄
3. Conda 环境激活
   - 自动执行 `conda activate make_image`
4. 启动命令
   - 前端：`npm run dev -- --host 0.0.0.0 --port <PORT>`
   - 后端：`uvicorn backend.main:app --host <HOST> --port <PORT>`
5. 错误处理
   - 端口检测失败、环境激活失败、启动失败等情况都会输出明确的错误信息并退出

## 使用示例
```bash
# 启动前端（默认端口 3000）
./start_frontend.sh

# 启动前端到自定义端口 3001
./start_frontend.sh 3001

# 启动后端（默认端口 8000）
./start_backend.sh

# 启动后端到自定义端口 5000
./start_backend.sh 5000

# 指定日志目录并启动后端
LOG_DIR=/var/log/myapp ./start_backend.sh
```

## 权限设置
脚本创建后请设置可执行权限：
```bash
chmod +x start_frontend.sh start_backend.sh
```

## 常见问题
- 若提示未找到 `conda`，请确认 Conda 已安装并在当前 Shell 中可用
- 若提示未找到 `uvicorn`，请在激活的环境中执行 `pip install uvicorn[standard]`
- 若端口释放失败，脚本仍会尝试启动；可手动检查并终止残留进程后重试

