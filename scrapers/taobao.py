"""
淘宝/天猫爬虫
支持 WAP 页面 + PC 页面两种策略
"""

import re
from typing import Optional, Dict
from scrapers.base import BaseScraper


class TaobaoScraper(BaseScraper):
    
    def __init__(self):
        super().__init__()
        self.session.headers.update({
            "Referer": "https://www.taobao.com/",
            "Accept-Language": "zh-CN,zh;q=0.9",
        })
    
    @property
    def platform_name(self) -> str:
        return "taobao"
    
    def extract_product_id(self, url: str) -> Optional[str]:
        m = re.search(r'[?&]id=(\d+)', url)
        if m:
            return f"taobao_{m.group(1)}"
        m = re.search(r'tmall\.com/item\.htm\?id=(\d+)', url)
        if m:
            return f"tmall_{m.group(1)}"
        return None
    
    async def get_price(self, url: str) -> Optional[Dict]:
        product_id = self.extract_product_id(url)
        if not product_id:
            print(f"[Taobao] 无法从URL解析商品ID: {url}")
            return None
        
        item_id = product_id.split("_")[1]

        # 策略1: WAP 手机版（反爬弱一些）
        result = await self._get_price_wap(item_id)
        if result:
            result["url"] = url
            return result
        
        # 策略2: PC 页面解析
        result = await self._get_price_page(url, item_id)
        if result:
            result["url"] = url
            return result
        
        return None
    
    async def _get_price_wap(self, item_id: str) -> Optional[Dict]:
        """手机版淘宝/WAP页面（成功率较高）"""
        wap_url = f"https://h5.m.taobao.com/awp/core/detail.htm?id={item_id}"
        resp = self._get_with_retry(wap_url, headers={
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15",
            "Accept": "text/html",
        })

        if not resp:
            return None

        try:
            text = resp.text
            price = None
            name = None

            # 匹配各种价格格式
            for pattern in [
                r'"price"\s*:\s*"?([\d.]+)"?',
                r'"currentPrice"\s*:\s*"?([\d.]+)"?',
                r'"promotionPrice"\s*:\s*"?([\d.]+)"?',
                r'priceAmount\s*:\s*"?([\d.]+)"?',
            ]:
                m = re.search(pattern, text)
                if m:
                    price = float(m.group(1))
                    break

            # 匹配商品名称
            name_patterns = [
                r'"title"\s*:\s*"([^"]+)"',
                r'<title>([^<]+)</title>',
            ]
            for np in name_patterns:
                nm = re.search(np, text)
                if nm:
                    name = nm.group(1).strip()
                    break

            if price:
                return {
                    "price": price,
                    "name": name or f"taobao_{item_id}",
                    "platform": "taobao",
                }
        except Exception as e:
            print(f"[Taobao WAP] 解析失败: {e}")

        return None
    
    async def _get_price_page(self, url: str, item_id: str) -> Optional[Dict]:
        """PC 页面解析"""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.taobao.com/",
        }
        resp = self._get_with_retry(url, headers=headers)
        
        if not resp:
            return None
        
        try:
            text = resp.text
            
            # 提取价格
            price = None
            for pattern in [
                r'"price"\s*:\s*"?([\d.]+)"?',
                r'"currentPrice"\s*:\s*"?([\d.]+)"?',
                r'"promotionPrice"\s*:\s*"?([\d.]+)"?',
            ]:
                m = re.search(pattern, text)
                if m:
                    price = float(m.group(1))
                    break
            
            # 提取名称
            name = None
            for pattern in [r'"title"\s*:\s*"([^"]+)"', r'<title>([^<]+)</title>']:
                nm = re.search(pattern, text)
                if nm:
                    name = nm.group(1).strip()
                    break
            
            if price:
                return {
                    "price": price,
                    "name": name or f"taobao_{item_id}",
                    "platform": "taobao",
                }
        except Exception as e:
            print(f"[Taobao PC] 解析失败: {e}")
        
        return None
    
    def _parse_price(self, text: str) -> Optional[float]:
        if not text:
            return None
        text = text.replace("¥", "").replace("￥", "").replace(",", "").strip()
        try:
            return float(text)
        except ValueError:
            m = re.search(r"(\d+\.?\d*)", text)
            if m:
                return float(m.group(1))
        return None