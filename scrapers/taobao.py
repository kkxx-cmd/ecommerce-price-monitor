"""
淘宝爬虫
支持 WAP 页面 + API 两种策略
注意：淘宝反爬很强，建议配合代理池使用
"""

import re
import json
import time
import asyncio
from typing import Optional, Dict
from bs4 import BeautifulSoup
from scrapers.base import BaseScraper


class TaobaoScraper(BaseScraper):
    
    def __init__(self):
        super().__init__()
        # 淘宝需要特殊 headers
        self.session.headers.update({
            "Referer": "https://www.taobao.com/",
            "Accept-Language": "zh-CN,zh;q=0.9",
        })
    
    @property
    def platform_name(self) -> str:
        return "taobao"
    
    def extract_product_id(self, url: str) -> Optional[str]:
        # https://item.taobao.com/item.htm?id=582843123456
        m = re.search(r'[?&]id=(\d+)', url)
        if m:
            return f"taobao_{m.group(1)}"
        # 天猫链接
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
        
        # 策略2: 解析 PC 页面
        result = await self._get_price_page(url, item_id)
        if result:
            result["url"] = url
            return result
        
        return None
    
    async def _get_price_wap(self, item_id: str) -> Optional[Dict]:
        """手机版淘宝/WAP页面"""
        wap_url = f"https://h5.m.taobao.com/awp/core/detail.htm?id={item_id}"
        resp = self._get_with_retry(wap_url, headers={
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15"
        })
        
        if not resp:
            return None
        
        try:
            soup = BeautifulSoup(resp.text, "lxml")
            
            # 尝试从页面提取价格
            price_elem = (
                soup.select_one("[class*='price']") or
                soup.select_one("[class*='Price']") or
                soup.select_one("[data-price]")
            )
            
            if price_elem:
                price_text = price_elem.get("data-price") or price_elem.get_text(strip=True)
                price = self._parse_price(price_text)
                if price:
                    return {"price": price, "name": f"taobao_{item_id}", "platform": "taobao"}
            
            # 尝试从script提取
            scripts = soup.find_all("script")
            for script in scripts:
                text = script.string or ""
                price_m = re.search(r'"price":\s*"?(\d+\.?\d*)"?', text)
                if price_m:
                    return {
                        "price": float(price_m.group(1)),
                        "name": f"taobao_{item_id}",
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
            soup = BeautifulSoup(resp.text, "lxml")
            
            # 提取商品名称
            name = ""
            name_elem = soup.select_one("h3.tb-main-title") or soup.select_one("[class*='title']") or soup.select_one("title")
            if name_elem:
                name = name_elem.get_text(strip=True)
            if not name:
                title = soup.find("title")
                if title:
                    name = title.get_text(strip=True).split("\n")[0].strip()
            
            # 提取价格（淘宝价格通常在特定script标签里）
            script_texts = [s.string for s in soup.find_all("script") if s.string]
            price = None
            for text in script_texts:
                # 匹配 "price":"xxx.xx" 或 "price":123.45
                for pattern in [r'"price"\s*:\s*"?(\d+\.?\d*)"?', r'"currentPrice"\s*:\s*"?(\d+\.?\d*)"?']:
                    m = re.search(pattern, text)
                    if m:
                        price = float(m.group(1))
                        break
                if price:
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
        """从文本提取价格"""
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