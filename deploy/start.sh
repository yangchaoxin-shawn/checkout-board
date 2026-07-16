#!/bin/bash
set -eu
# ====================================================
# 每日作战打卡看板 — 启动脚本
# 用法：./deploy/start.sh
# ====================================================

cd "$(dirname "$0")/.."

echo "========================================"
echo "  每日作战打卡看板 — 启动"
echo "========================================"

# 1. 检查 docker 环境
echo "[1/3] 检查 Docker 环境..."
command -v docker >/dev/null 2>&1 || { echo "✗ 未检测到 docker，请先安装 Docker"; exit 1; }
docker compose version >/dev/null 2>&1 || { echo "✗ 未检测到 docker compose，请先安装"; exit 1; }
echo "  ✓ Docker 就绪"

# 2. 检查 .env 是否配置
echo "[2/3] 检查环境变量..."
if [ ! -f .env ]; then
    echo "  ! .env 不存在，从 .env.example 复制（请务必修改密码）"
    cp .env.example .env
    echo "  ! 请编辑 .env 设置 CHECKIN_PASSWORD 和 CHECKIN_SECRET"
    echo "  ! 编辑完成后重新运行即可"
    exit 0
fi
echo "  ✓ .env 已存在"

# 3. 启动服务
echo "[3/3] 启动服务..."
docker compose up -d
echo ""
echo "  ✓ 服务已启动！"
echo ""
echo "  服务状态："
docker compose ps
echo ""
echo "  → 查看日志：./deploy/logs.sh"
echo "  → 停止服务：./deploy/stop.sh"
echo "========================================"
