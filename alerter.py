"""
Telegram 告警通知
"""

import os
import httpx
from typing import List, Dict, Optional
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

# emoji映射
EMOJI_PLATFORM = {
    "jd": "🟠",
    "taobao": "🟠", 
    "pdd": "🟡",
    "jd_price_up": "📈",
    "jd_price_down": "📉",
    "taobao_price_up": "📈",
    "taobao_price_down": "📉",
    "pdd_price_up": "📈",
    "pdd_price_down": "📉",
}

EMOJI_UP = "🔴"
EMOJI_DOWN = "🟢"


def build_price_message(product: Dict, price_info: Dict) -> str:
    """构建单条价格变化消息"""
    platform = product.get("platform", "")
    name = product.get("name", "未知商品")
    old_price = price_info.get("prev")
    new_price = price_info.get("new")
    change_pct = price_info.get("change_pct", 0)
    
    emoji = EMOJI_PLATFORM.get(platform, "🏷️")
    direction = EMOJI_DOWN if change_pct < 0 else EMOJI_UP
    
    msg_lines = [
        f"{emoji} *{name}*",
        f"平台: {platform.upper()}",
        f"",
        f"💰 原价: `¥{old_price:.2f}`",
        f"💰 新价: `¥{new_price:.2f}`",
        f"",
        f"{direction} 变化: `{change_pct:+.2f}%`",
        f"",
        f"🔗 [查看商品]({product.get('url', '')})",
    ]
    
    return "\n".join(msg_lines)


def build_daily_summary(products: List[Dict]) -> str:
    """构建每日汇总消息"""
    lines = [
        "📊 *每日价格监控汇总*",
        f"🕐 {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
    ]
    
    for p in products:
        emoji = EMOJI_PLATFORM.get(p.get("platform", ""), "🏷️")
        lines.append(f"{emoji} *{p['name']}*")
        lines.append(f"   当前: `¥{p['current_price']:.2f}` | 最低: `¥{p['lowest_price']:.2f}` | 最高: `¥{p['highest_price']:.2f}`")
        lines.append("")
    
    return "\n".join(lines)


async def send_telegram(text: str, parse_mode: str = "Markdown") -> bool:
    """发送 Telegram 消息"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"[Telegram] 未配置，跳过发送: {text[:50]}...")
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }
    
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(url, json=payload)
            data = resp.json()
            if data.get("ok"):
                print(f"[Telegram] 发送成功")
                return True
            else:
                print(f"[Telegram] 发送失败: {data}")
                return False
    except Exception as e:
        print(f"[Telegram] 发送异常: {e}")
        return False


def send_sync(text: str, parse_mode: str = "Markdown") -> bool:
    """同步版本发送"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"[Telegram] 未配置，跳过发送")
        return False
    
    import requests
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=15)
        data = resp.json()
        return data.get("ok", False)
    except Exception as e:
        print(f"[Telegram] 发送异常: {e}")
        return False


def notify_price_change(product: Dict, price_info: Dict) -> bool:
    """通知价格变化（同步）"""
    msg = build_price_message(product, price_info)
    return send_sync(msg)


def notify_daily_summary(products: List[Dict]) -> bool:
    """发送每日汇总"""
    if not products:
        return False
    msg = build_daily_summary(products)
    return send_sync(msg)