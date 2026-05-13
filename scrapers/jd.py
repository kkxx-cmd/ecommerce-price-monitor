"""
京东爬虫
支持 PC 页面解析 + 移动 API 两种策略
"""

import re
import asyncio
from typing import Optional, Dict
from bs4 import BeautifulSoup
from scrapers.base import BaseScraper


class JDScraper(BaseScraper):
    
    @property
    def platform_name(self) -> str:
        return "jd"
    
    def extract_product_id(self, url: str) -> Optional[str]:
        # https://item.jd.com/100012043.html
        m = re.search(r'item\.jd\.com/(\d+)\.html', url)
        if m:
            return f"jd_{m.group(1)}"
        
        # https:// Union JD URL
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
        
        # 策略1: 移动端 API（较轻量，成功率高）
        result = await self._get_price_mobile_api(sku_id)
        if result:
            result["url"] = url
            return result
        
        # 策略2: PC 页面解析（兜底）
        result = await self._get_price_page(url, sku_id)
        if result:
            result["url"] = url
            return result
        
        return None
    
    async def _get_price_mobile_api(self, sku_id: str) -> Optional[Dict]:
        """京东移动端价格 API"""
        # 这个接口有时效性，可能需要更新
        api_url = "https://api.m.jd.com/api"
        params = {
            "appid": "item-v3",
            "functionId": "pc_basic_data_get",
            "skuId": sku_id,
            "client": "pc",
            "clientVersion": "9.0.0",
            "uuid": "",
            "scVal": "",
        }
        headers = {
            "referer": f"https://item.jd.com/{sku_id}.html",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
        
        resp = self._get_with_retry(api_url, params=params, headers=headers)
        if not resp:
            return None
        
        try:
            data = resp.json()
            # 解析返回结构（结构可能随版本变化，兜底处理）
            if "data" in data:
                price = data["data"].get("price", {})
                if isinstance(price, dict):
                    return {
                        "price": float(price.get("p", 0)),
                        "name": data["data"].get("productInfo", {}).get("name", "京东商品"),
                        "platform": "jd",
                    }
        except Exception as e:
            print(f"[JD] API解析失败: {e}")
        
        return None
    
    async def _get_price_page(self, url: str, sku_id: str) -> Optional[Dict]:
        """直接解析 PC 页面"""
        # 先尝试获取页面中的价格
        price_api = f"https://p.3.cn/prices/mgets?skuIds=J_{sku_id}"
        price_resp = self._get_with_retry(price_api)
        
        if price_resp:
            try:
                import json
                prices = price_resp.json()
                if prices and len(prices) > 0:
                    price_str = prices[0].get("p", "")
                    if price_str:
                        return {
                            "price": float(price_str),
                            "name": f"jd_{sku_id}",  # 页面单独获取name
                            "platform": "jd",
                        }
            except Exception as e:
                print(f"[JD] 价格API解析失败: {e}")
        
        # 解析商品详情页获取名称
        resp = self._get_with_retry(url)
        if not resp:
            return None
        
        try:
            soup = BeautifulSoup(resp.text, "lxml")
            
            # 获取商品名称
            name = ""
            name_elem = soup.select_one("div.p-name em") or soup.select_one("h1.product-title") or soup.select_one("[class*='title']")
            if name_elem:
                name = name_elem.get_text(strip=True)
            else:
                title = soup.find("title")
                if title:
                    name = title.get_text(strip=True).split("_")[0].split("-")[0].strip()
            
            if not name:
                name = f"jd_{sku_id}"
            
            return {
                "price": 0,  # 价格在API中单独获取
                "name": name,
                "platform": "jd",
            }
        except Exception as e:
            print(f"[JD] 页面解析失败: {e}")
        
        return None


# 独立的快速价格查询函数（推荐使用）
def get_jd_price_quick(sku_id: str) -> Optional[float]:
    """
    快速获取京东价格 - 走官方价格API
    sku_id: 商品SKU数字ID，如 100012043
    """
    import httpx
    price_api = f"https://p.3.cn/prices/mgets?skuIds=J_{sku_id}"
    headers = {
        "User-Agent": "Mozilla/5.0",
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
    """从京东页面提取商品名称"""
    import httpx
    from bs4 import BeautifulSoup
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        resp = httpx.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(resp.text, "lxml")
        title = soup.find("title")
        if title:
            # 通常格式: "商品名称 - 京东"
            name = title.get_text(strip=True).split(" - ")[0].strip()
            return name
    except Exception as e:
        print(f"[JD名称] {e}")
    return None