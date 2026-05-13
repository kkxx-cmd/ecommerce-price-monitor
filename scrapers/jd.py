"""
京东爬虫
支持 PC 页面解析 + 移动 API 两种策略

注意：京东对境外 IP 有严格风控（item.jd.com 可能 redirect 到首页，
p.3.cn 价格 API 可能 DNS 解析失败）。
国内 VPS 上运行可完全正常，境外机器请用 --test 单独验证。
"""

import re
import json
from typing import Optional, Dict
from bs4 import BeautifulSoup
from scrapers.base import BaseScraper


class JDScraper(BaseScraper):

    @property
    def platform_name(self) -> str:
        return "jd"

    def extract_product_id(self, url: str) -> Optional[str]:
        m = re.search(r'item\.jd\.com/(\d+)\.html', url)
        if m:
            return f"jd_{m.group(1)}"
        m = re.search(r'jd\.com/(\d+)\.html', url)
        if m:
            return f"jd_{m.group(1)}"
        return None

    async def get_price(self, url: str) -> Optional[Dict]:
        product_id = self.extract_product_id(url)
        if not product_id:
            print(f"[JD] 无法从URL解析商品ID: {url}")
            return None

        sku_id = product_id.split("_")[1]

        # 策略1: 直接用价格 API（国内 VPS 常用，成功率最高）
        result = self._get_price_api(sku_id)
        if result:
            result["url"] = url
            result["name"] = self._get_name_from_page(url) or f"jd_{sku_id}"
            return result

        # 策略2: 解析 PC 页面（境外 IP 可能返回首页，需验证返回内容）
        result = await self._get_price_page(url, sku_id)
        if result:
            result["url"] = url
            return result

        return None

    def _get_price_api(self, sku_id: str) -> Optional[Dict]:
        """京东官方价格 API（推荐）"""
        import httpx
        price_api = f"https://p.3.cn/prices/mgets?skuIds=J_{sku_id}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": f"https://item.jd.com/{sku_id}.html",
        }
        try:
            resp = httpx.get(price_api, headers=headers, timeout=10)
            prices = resp.json()
            if prices and prices[0].get("p"):
                price = float(prices[0]["p"])
                return {"price": price, "name": f"jd_{sku_id}", "platform": "jd"}
        except Exception as e:
            print(f"[JD API] 失败: {e}")
        return None

    def _get_name_from_page(self, url: str) -> Optional[str]:
        """从商品页提取名称（国内 VPS 可用）"""
        import httpx
        from bs4 import BeautifulSoup
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        try:
            resp = httpx.get(url, headers=headers, timeout=10, follow_redirects=False)
            # 如果被重定向到了 jd.com 首页，说明是境外 IP
            if resp.status_code == 302 and "jd.com" in resp.headers.get("location", ""):
                print("[JD] 检测到境外 IP 跳转，商品详情不可用")
                return None
            soup = BeautifulSoup(resp.text, "lxml")
            title = soup.find("title")
            if title:
                name = title.get_text(strip=True).split("-")[0].strip()
                if name and "JD" not in name and "京东" not in name:
                    return name
        except Exception as e:
            print(f"[JD 名称] {e}")
        return None

    async def _get_price_page(self, url: str, sku_id: str) -> Optional[Dict]:
        """解析 PC 页面（国内 VPS 专用）"""
        import httpx
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.jd.com/",
        }
        try:
            resp = httpx.get(url, headers=headers, timeout=15, follow_redirects=False)
            if resp.status_code == 302:
                loc = resp.headers.get("location", "")
                if "jd.com" in loc and "item.jd.com" not in loc:
                    print("[JD] 被重定向到首页，跳过页面解析")
                    return None

            soup = BeautifulSoup(resp.text, "lxml")
            title = soup.find("title")
            name = title.get_text(strip=True).split("-")[0].strip() if title else f"jd_{sku_id}"

            # 尝试从页面 script 提取价格
            for script in soup.find_all("script"):
                text = script.string or ""
                m = re.search(r'"price"\s*:\s*"?(\d+\.?\d*)"?', text)
                if m:
                    return {"price": float(m.group(1)), "name": name, "platform": "jd"}

        except Exception as e:
            print(f"[JD 页面] 解析失败: {e}")
        return None


# 独立的快速价格查询函数（国内 VPS 使用）
def get_jd_price_quick(sku_id: str) -> Optional[float]:
    """快速获取京东价格 - 走官方价格API"""
    import httpx
    price_api = f"https://p.3.cn/prices/mgets?skuIds=J_{sku_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": f"https://item.jd.com/{sku_id}.html",
    }
    try:
        resp = httpx.get(price_api, headers=headers, timeout=10)
        prices = resp.json()
        if prices and prices[0].get("p"):
            return float(prices[0]["p"])
    except Exception as e:
        print(f"[JD价格API] {e}")
    return None


def get_jd_name_from_page(url: str) -> Optional[str]:
    """从京东页面提取商品名称（国内 VPS）"""
    import httpx
    from bs4 import BeautifulSoup
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        resp = httpx.get(url, headers=headers, timeout=10, follow_redirects=False)
        if resp.status_code == 302:
            return None
        soup = BeautifulSoup(resp.text, "lxml")
        title = soup.find("title")
        if title:
            name = title.get_text(strip=True).split(" - ")[0].strip()
            return name
    except:
        pass
    return None