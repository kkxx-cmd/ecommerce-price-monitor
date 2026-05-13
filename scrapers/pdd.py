"""
拼多多爬虫
PDD 反爬非常强，建议优先用其开放 API 接口
"""

import re
import hashlib
import time
import json
from typing import Optional, Dict
from bs4 import BeautifulSoup
from scrapers.base import BaseScraper


class PDDScraper(BaseScraper):
    
    @property
    def platform_name(self) -> str:
        return "pdd"
    
    def extract_product_id(self, url: str) -> Optional[str]:
        # https://youk米.pinduoduo.com/goods/goods-detail.html?goodsId=xxx
        # https://mobile.pinduoduo.com/goods.html?goodsId=xxx
        m = re.search(r'goodsId=(\d+)', url)
        if m:
            return f"pdd_{m.group(1)}"
        m = re.search(r'pinduoduo\.com/goods/goods-detail\.html\?goodsId=(\d+)', url)
        if m:
            return f"pdd_{m.group(1)}"
        return None
    
    async def get_price(self, url: str) -> Optional[Dict]:
        product_id = self.extract_product_id(url)
        if not product_id:
            print(f"[PDD] 无法从URL解析商品ID: {url}")
            return None
        
        goods_id = product_id.split("_")[1]
        
        # 策略1: 走拼多多移动端页面
        result = await self._get_price_mobile(url, goods_id)
        if result:
            result["url"] = url
            return result
        
        # 策略2: PC 页面解析
        result = await self._get_price_pc(url, goods_id)
        if result:
            result["url"] = url
            return result
        
        return None
    
    async def _get_price_mobile(self, url: str, goods_id: str) -> Optional[Dict]:
        """移动端页面解析"""
        # 去掉 goodsId 参数，用移动端格式
        mobile_url = f"https://mobile.pinduoduo.com/goods.html?goodsId={goods_id}"
        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15",
            "Referer": "https://mobile.pinduoduo.com/",
        }
        
        resp = self._get_with_retry(mobile_url, headers=headers)
        if not resp:
            return None
        
        try:
            soup = BeautifulSoup(resp.text, "lxml")
            
            # 提取价格
            price = None
            
            # 方法1: 找价格元素
            price_elem = (
                soup.select_one("[class*='price']") or
                soup.select_one("[class*='Price']") or
                soup.select_one("[data-price]")
            )
            if price_elem:
                price_text = price_elem.get("data-price") or price_elem.get_text(strip=True)
                price = self._parse_price(price_text)
            
            # 方法2: 从script中找
            if not price:
                scripts = soup.find_all("script")
                for script in scripts:
                    text = script.string or ""
                    # PDD 常见格式: window.__REQUIRE_PRICE__ 或直接price字段
                    price_m = re.search(r'"price"\s*:\s*"?(\d+\.?\d*)"?', text)
                    if price_m:
                        price = float(price_m.group(1))
                        break
            
            # 方法3: 搜索 JSON 数据
            if not price:
                text = resp.text
                for pattern in [
                    r'"price"\s*:\s*(\d+\.?\d*)',
                    r'"lowestPrice"\s*:\s*(\d+\.?\d*)',
                    r'"groupPrice"\s*:\s*(\d+\.?\d*)',
                ]:
                    m = re.search(pattern, text)
                    if m:
                        price = float(m.group(1))
                        break
            
            if price:
                return {
                    "price": price,
                    "name": f"pdd_{goods_id}",
                    "platform": "pdd",
                }
        except Exception as e:
            print(f"[PDD Mobile] 解析失败: {e}")
        
        return None
    
    async def _get_price_pc(self, url: str, goods_id: str) -> Optional[Dict]:
        """PC 页面解析"""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://youk米.pinduoduo.com/",
        }
        resp = self._get_with_retry(url, headers=headers)
        
        if not resp:
            return None
        
        try:
            soup = BeautifulSoup(resp.text, "lxml")
            
            # PDD PC 页面价格通常在 script 中
            scripts = soup.find_all("script")
            for script in scripts:
                text = script.string or ""
                for pattern in [
                    r'"price"\s*:\s*"?(\d+\.?\d*)"?',
                    r'"lowestPrice"\s*:\s*"?(\d+\.?\d*)"?',
                    r'"groupPrice"\s*:\s*"?(\d+\.?\d*)"?',
                ]:
                    m = re.search(pattern, text)
                    if m:
                        return {
                            "price": float(m.group(1)),
                            "name": f"pdd_{goods_id}",
                            "platform": "pdd",
                        }
        except Exception as e:
            print(f"[PDD PC] 解析失败: {e}")
        
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