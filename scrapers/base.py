"""
基础爬虫类
"""

import time
import random
import httpx
from abc import ABC, abstractmethod
from typing import Optional, Dict, List
from config import DEFAULT_HEADERS, REQUEST_DELAY_MIN, REQUEST_DELAY_MAX, MAX_RETRIES


class BaseScraper(ABC):
    """所有爬虫的基类"""
    
    def __init__(self):
        self.session = httpx.Client(
            headers=DEFAULT_HEADERS.copy(),
            timeout=30,
            follow_redirects=True,
        )
    
    def _random_delay(self):
        """随机延时，模拟人类行为"""
        delay = random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX)
        time.sleep(delay)
    
    def _get_with_retry(self, url: str, **kwargs) -> Optional[httpx.Response]:
        """带重试的GET请求"""
        for attempt in range(MAX_RETRIES):
            try:
                self._random_delay()
                resp = self.session.get(url, **kwargs)
                if resp.status_code == 200:
                    return resp
                elif resp.status_code == 403 or resp.status_code == 429:
                    print(f"[{self.platform_name}] 被反爬 (status={resp.status_code})，等待后重试...")
                    time.sleep(random.uniform(5, 15))
                else:
                    print(f"[{self.platform_name}] HTTP {resp.status_code}")
            except httpx.RequestError as e:
                print(f"[{self.platform_name}] 请求异常 (attempt {attempt+1}): {e}")
                time.sleep(2 ** attempt)
        return None
    
    @property
    @abstractmethod
    def platform_name(self) -> str:
        """平台名称"""
        pass
    
    @abstractmethod
    def extract_product_id(self, url: str) -> Optional[str]:
        """从URL提取商品ID"""
        pass
    
    @abstractmethod
    async def get_price(self, url: str) -> Optional[Dict]:
        """
        获取商品价格
        返回: {"price": float, "name": str, "platform": str, "url": str} 或 None
        """
        pass
    
    async def monitor(self, url: str) -> Optional[Dict]:
        """监控单个商品（模板方法）"""
        return await self.get_price(url)
    
    def close(self):
        self.session.close()