# 电商价格监控 - 快速测试脚本
# 在国内 VPS 上运行，验证爬虫是否正常工作

import asyncio
import sys
sys.path.insert(0, "/home/qgg/.openclaw/workspace/price-monitor-repo")

from scrapers.jd import JDScraper
from scrapers.taobao import TaobaoScraper
from scrapers.pdd import PDDScraper

TEST_URLS = {
    "京东": "https://item.jd.com/100012043.html",
    "淘宝": "https://item.taobao.com/item.htm?id=601841723756",
    "拼多多": "https://youk米.pinduoduo.com/goods/goods-detail.html?goodsId=10100058627417",
}

async def main():
    for name, url in TEST_URLS.items():
        print(f"\n{'='*50}")
        print(f"测试 {name}: {url}")
        
        if "jd.com" in url:
            scraper = JDScraper()
        elif "taobao" in url:
            scraper = TaobaoScraper()
        elif "pinduoduo" in url:
            scraper = PDDScraper()
        else:
            continue
        
        result = await scraper.get_price(url)
        scraper.close()
        
        if result:
            print(f"✅ 成功! 价格: ¥{result.get('price', 0):.2f} | 名称: {result.get('name', 'N/A')}")
        else:
            print("❌ 获取失败（可能是反爬或网络问题）")

if __name__ == "__main__":
    asyncio.run(main())