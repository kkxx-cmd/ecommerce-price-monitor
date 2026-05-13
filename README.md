# 🛒 电商价格监控系统

自动监控京东、淘宝、拼多多商品价格，价格变化时推送 Telegram 通知。

## 功能特性

- ✅ 支持京东 / 淘宝 / 拼多多 三大平台
- ✅ 价格变化自动告警（可配置阈值）
- ✅ 历史价格记录（SQLite 数据库）
- ✅ GitHub Actions 定时执行（免费）
- ✅ Telegram 通知推送
- ✅ 全程本地运行，不依赖第三方服务

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置商品

在 `data/products.json` 中添加要监控的商品：

```json
{
  "jd_100012043": {
    "platform": "jd",
    "name": "iPhone 15",
    "url": "https://item.jd.com/100012043.html"
  },
  "taobao_582843": {
    "platform": "taobao",
    "name": "AirPods Pro",
    "url": "https://item.taobao.com/item.htm?id=582843123456"
  }
}
```

或使用命令行添加：

```bash
python main.py --add https://item.jd.com/100012043.html "iPhone 15"
```

### 3. 配置 Telegram（可选）

设置环境变量：

```bash
export TELEGRAM_BOT_TOKEN="your-bot-token"
export TELEGRAM_CHAT_ID="your-chat-id"
```

### 4. 运行监控

```bash
# 立即执行一次监控
python main.py

# 列出所有商品
python main.py --list

# 测试单个商品
python main.py --test https://item.jd.com/100012043.html

# 发送每日汇总
python main.py --summary
```

## GitHub Actions 自动运行

### 设置步骤

1. **Fork 本仓库**

2. **添加 Secrets**（Settings → Secrets and variables → Actions）：
   - `TELEGRAM_BOT_TOKEN`: 你的 Telegram Bot Token
   - `TELEGRAM_CHAT_ID`: 你的 Telegram Chat ID

3. **修改 `data/products.json`**，填入你要监控的商品

4. **Push 即可自动运行**

默认每天 9:00、12:00、18:00、21:00 (UTC) 执行，可在 `.github/workflows/price-monitor.yml` 中修改

## 项目结构

```
ecommerce-price-monitor/
├── config.py          # 配置管理
├── database.py        # SQLite 数据库
├── alerter.py         # Telegram 告警
├── main.py            # 主入口
├── scrapers/
│   ├── base.py        # 基础爬虫类
│   ├── jd.py          # 京东爬虫
│   ├── taobao.py      # 淘宝爬虫
│   └── pdd.py         # 拼多多爬虫
├── .github/workflows/
│   └── price-monitor.yml  # GitHub Actions
├── data/
│   ├── products.json  # 商品配置
│   └── prices.db      # 价格历史数据库（自动生成）
└── requirements.txt
```

## 注意事项

- ⚠️ 三大平台均有反爬机制，本项目使用多策略应对（延时、UA随机化、备用API）
- ⚠️ 高频请求仍可能触发风控，建议设置合理的请求间隔
- 💡 如遇持续拦截，可考虑接入代理池或第三方比价API

## 免责声明

本工具仅供个人学习研究使用，请遵守各平台服务条款。