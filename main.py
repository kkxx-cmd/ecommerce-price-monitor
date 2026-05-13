"""
电商价格监控 - 主入口
用法:
  python main.py                    # 监控所有配置的商品
  python main.py --list             # 列出所有商品
  python main.py --add <url> <name> # 添加商品
  python main.py --test <url>       # 测试单个商品
"""

import asyncio
import argparse
import json
import sys
import os
from pathlib import Path
from typing import Dict, List

from config import DATA_DIR, load_products
from database import (
    upsert_product, record_price, record_alert,
    get_all_products, get_latest_price, get_product_history,
    get_pending_alerts, mark_alert_notified
)
from alerter import notify_price_change, notify_daily_summary
from scrapers.jd import JDScraper, get_jd_price_quick, get_jd_name_from_page
from scrapers.taobao import TaobaoScraper
from scrapers.pdd import PDDScraper


SCRAPERS = {
    "jd": JDScraper(),
    "taobao": TaobaoScraper(),
    "pdd": PDDScraper(),
}


async def get_scraper(platform: str):
    return SCRAPERS.get(platform.lower())


async def monitor_product(product_id: str, product: Dict) -> Dict:
    """监控单个商品"""
    url = product["url"]
    platform = product["platform"]
    name = product.get("name", product_id)
    
    print(f"  🔍 监控 [{platform}] {name}...")
    
    scraper = await get_scraper(platform)
    if not scraper:
        print(f"  ⚠️ 未知平台: {platform}")
        return None
    
    try:
        result = await scraper.get_price(url)
        if not result:
            print(f"  ❌ 获取价格失败")
            return None
        
        # 获取/补充价格
        price = result.get("price", 0)
        
        # 京东特殊处理：价格 API 单独调用
        if platform == "jd" and price == 0:
            sku_m = product_id.split("_")[1] if "_" in product_id else None
            if sku_m:
                real_price = get_jd_price_quick(sku_m)
                if real_price:
                    price = real_price
        
        # 补充商品名称
        if not result.get("name") or result["name"] in ["", product_id]:
            if platform == "jd":
                result["name"] = get_jd_name_from_page(url) or name
            else:
                result["name"] = name
        
        # 写入数据库
        upsert_product(product_id, platform, result.get("name", name), url, price)
        price_change = record_price(product_id, price)
        
        if price_change:
            change_pct = price_change["change_pct"]
            alert_type = "down" if change_pct < 0 else "up"
            record_alert(product_id, price_change["prev"], price_change["new"], change_pct, alert_type)
            
            result["change"] = price_change
            print(f"  ✅ 价格: ¥{price:.2f} ({change_pct:+.2f}%)")
        else:
            print(f"  ✅ 价格: ¥{price:.2f} (无变化)")
        
        return result
        
    except Exception as e:
        print(f"  ❌ 异常: {e}")
        return None
    finally:
        scraper.close()


async def run_monitoring():
    """运行全量监控"""
    products = load_products()
    
    if not products:
        print("⚠️  未配置商品，请先添加监控商品:")
        print("  python main.py --add <url> <name>")
        print("")
        print("  示例:")
        print("  python main.py --add https://item.jd.com/100012043.html 'iPhone 15'")
        print("  python main.py --add https://item.taobao.com/item.htm?id=123456 '商品名称'")
        print("  python main.py --add https://youk米.pinduoduo.com/goods/goods-detail.html?goodsId=xxx '商品名称'")
        return
    
    print(f"📦 共 {len(products)} 个商品，开始监控...\n")
    
    results = []
    for pid, pdata in products.items():
        if not isinstance(pdata, dict):
            continue  # 跳过非商品配置（如注释字段）
        result = await monitor_product(pid, pdata)
        results.append(result)
    
    print(f"\n✅ 监控完成，共处理 {len([r for r in results if r])} 个商品")


async def test_product(url: str):
    """测试单个 URL"""
    print(f"🔍 测试: {url}\n")
    
    # 识别平台
    platform = None
    if "jd.com" in url:
        platform = "jd"
    elif "taobao.com" in url or "tmall.com" in url:
        platform = "taobao"
    elif "pinduoduo.com" in url:
        platform = "pdd"
    
    if not platform:
        print("❌ 未知平台")
        return
    
    print(f"平台: {platform}")
    
    scraper = await get_scraper(platform)
    if not scraper:
        return
    
    result = await scraper.get_price(url)
    scraper.close()
    
    if result:
        print(f"✅ 获取成功!")
        print(f"   价格: ¥{result.get('price', 0):.2f}")
        print(f"   名称: {result.get('name', '未知')}")
    else:
        print("❌ 获取失败（可能被反爬拦截）")


def add_product(url: str, name: str):
    """添加商品到监控列表"""
    products = load_products()
    
    # 自动识别平台并生成ID
    if "jd.com" in url:
        import re
        m = re.search(r'item\.jd\.com/(\d+)', url)
        pid = f"jd_{m.group(1)}" if m else f"jd_custom_{len(products)}"
        platform = "jd"
    elif "taobao.com" in url:
        m = re.search(r'[?&]id=(\d+)', url)
        pid = f"taobao_{m.group(1)}" if m else f"taobao_custom_{len(products)}"
        platform = "taobao"
    elif "tmall.com" in url:
        m = re.search(r'[?&]id=(\d+)', url)
        pid = f"tmall_{m.group(1)}" if m else f"tmall_custom_{len(products)}"
        platform = "taobao"
    elif "pinduoduo.com" in url:
        m = re.search(r'goodsId=(\d+)', url)
        pid = f"pdd_{m.group(1)}" if m else f"pdd_custom_{len(products)}"
        platform = "pdd"
    else:
        pid = f"custom_{len(products)}"
        platform = "unknown"
    
    products[pid] = {
        "platform": platform,
        "name": name,
        "url": url,
    }
    
    # 保存
    products_file = DATA_DIR / "products.json"
    products_file.parent.mkdir(exist_ok=True)
    with open(products_file, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 已添加: [{platform}] {name} (ID: {pid})")


def list_products():
    """列出所有商品"""
    products = load_products()
    if not products:
        print("暂无监控商品")
        return
    
    print(f"📦 共 {len(products)} 个商品:\n")
    for pid, pdata in products.items():
        current = get_latest_price(pid)
        print(f"  [{pdata['platform']:6}] {pdata['name']}")
        print(f"          ID: {pid}")
        print(f"          URL: {pdata['url']}")
        print(f"          最新价: {f'¥{current:.2f}' if current else '暂无'}")
        print()


def send_summary():
    """发送每日汇总到 Telegram"""
    products = get_all_products()
    if not products:
        print("暂无数据")
        return
    
    products_data = []
    for p in products:
        current = get_latest_price(p["id"])
        if current:
            products_data.append({
                "name": p["name"],
                "platform": p["platform"],
                "current_price": current,
                "lowest_price": p.get("lowest_price") or current,
                "highest_price": p.get("highest_price") or current,
            })
    
    if products_data:
        notify_daily_summary(products_data)


def main():
    parser = argparse.ArgumentParser(description="电商价格监控")
    parser.add_argument("--list", action="store_true", help="列出所有商品")
    parser.add_argument("--add", nargs=2, metavar=("URL", "NAME"), help="添加商品")
    parser.add_argument("--test", metavar="URL", help="测试单个商品")
    parser.add_argument("--summary", action="store_true", help="发送每日汇总到 Telegram")
    parser.add_argument("--alerts", action="store_true", help="处理待发送的告警")
    
    args = parser.parse_args()
    
    if args.list:
        list_products()
    elif args.add:
        add_product(args.add[0], args.add[1])
    elif args.test:
        asyncio.run(test_product(args.test))
    elif args.summary:
        send_summary()
    elif args.alerts:
        # 处理待发送的告警
        from alerter import send_sync
        pending = get_pending_alerts()
        print(f"待发送告警: {len(pending)}")
        # 在 CI 中通常由 cron job 触发，这里仅作保留接口
    else:
        asyncio.run(run_monitoring())


if __name__ == "__main__":
    main()