#!/bin/bash
# ============================================================
# 电商价格监控 - VPS 部署脚本
# 在国内 VPS 上运行此脚本即可完成安装
# ============================================================

set -e

REPO_URL="https://github.com/kkxx-cmd/ecommerce-price-monitor.git"
INSTALL_DIR="/opt/price-monitor"
LOG_DIR="/var/log/price-monitor"

echo "=========================================="
echo "  电商价格监控系统 - VPS 部署脚本"
echo "=========================================="

# 1. 安装依赖
echo "[1/5] 安装系统依赖..."
apt-get update -qq
apt-get install -y -qq python3 python3-pip git > /dev/null 2>&1

# 2. 克隆仓库
echo "[2/5] 拉取代码..."
if [ -d "$INSTALL_DIR" ]; then
    echo "  已有代码，更新中..."
    cd "$INSTALL_DIR" && git pull
else
    mkdir -p "$INSTALL_DIR"
    git clone "$REPO_URL" "$INSTALL_DIR"
fi

# 3. 安装 Python 依赖
echo "[3/5] 安装 Python 依赖..."
pip3 install -q -r "$INSTALL_DIR/requirements.txt"

# 4. 配置环境变量
echo "[4/5] 配置环境变量..."
if [ ! -f "$INSTALL_DIR/.env" ]; then
    cat > "$INSTALL_DIR/.env" << EOF
# Telegram 配置
TELEGRAM_BOT_TOKEN="your-bot-token-here"
TELEGRAM_CHAT_ID="your-chat-id-here"
EOF
    echo "  已创建 .env 模板，请编辑 $INSTALL_DIR/.env 填入真实 token"
else
    echo "  .env 已存在，跳过"
fi

# 5. 配置定时任务
echo "[5/5] 配置定时任务..."
CRON_JOB="0 9,12,18,21 * * * cd $INSTALL_DIR && python3 main.py --summary >> $LOG_DIR/monitor.log 2>&1"

# 检查是否已有这个 cron
if crontab -l 2>/dev/null | grep -q "ecommerce-price-monitor"; then
    echo "  定时任务已存在，跳过"
else
    mkdir -p "$LOG_DIR"
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo "  定时任务已添加（每天 9/12/18/21 点执行）"
fi

echo ""
echo "=========================================="
echo "  部署完成！"
echo "=========================================="
echo ""
echo "下一步："
echo "  1. 编辑 $INSTALL_DIR/.env 填入 Telegram Token"
echo "  2. 编辑 $INSTALL_DIR/data/products.json 添加监控商品"
echo "  3. 手动测试: cd $INSTALL_DIR && python3 main.py"
echo "  4. 查看日志: tail -f $LOG_DIR/monitor.log"
echo ""
echo "添加商品命令："
echo "  python3 main.py --add https://item.jd.com/100012043.html 'iPhone 15'"
echo "  python3 main.py --add https://item.taobao.com/item.htm?id=123456 '商品名称'"
echo "  python3 main.py --add https://youk米.pinduoduo.com/goods/goods-detail.html?goodsId=xxx '商品名称'"
echo ""