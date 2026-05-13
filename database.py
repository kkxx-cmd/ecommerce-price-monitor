"""
SQLite 价格数据库 - 记录价格历史
"""

import sqlite3
import json
from datetime import datetime, date
from pathlib import Path
from typing import Optional, List, Dict
from config import DB_PATH


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库表"""
    conn = get_connection()
    cur = conn.cursor()
    
    # 商品表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id TEXT PRIMARY KEY,
            platform TEXT NOT NULL,
            name TEXT NOT NULL,
            url TEXT NOT NULL,
            initial_price REAL,
            lowest_price REAL,
            highest_price REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 价格历史表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id TEXT NOT NULL,
            price REAL NOT NULL,
            currency TEXT DEFAULT '¥',
            scraped_at TEXT DEFAULT CURRENT_TIMESTAMP,
            source_page TEXT,
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)
    
    # 告警记录表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id TEXT NOT NULL,
            old_price REAL,
            new_price REAL,
            change_pct REAL,
            alert_type TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            notified INTEGER DEFAULT 0,
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)
    
    conn.commit()
    conn.close()


def upsert_product(product_id: str, platform: str, name: str, url: str, price: float) -> bool:
    """插入或更新商品，返回是否是新商品"""
    conn = get_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT id FROM products WHERE id = ?", (product_id,))
    existing = cur.fetchone()
    
    if existing is None:
        cur.execute(
            """INSERT INTO products
               (id, platform, name, url, initial_price, lowest_price, highest_price, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (product_id, platform, name, url, price, price, price, datetime.now().isoformat())
        )
        is_new = True
    else:
        # 更新最高/最低价
        cur.execute(
            """UPDATE products SET
               lowest_price = MIN(COALESCE(lowest_price, ?), ?),
               highest_price = MAX(COALESCE(highest_price, ?), ?),
               updated_at = ?
               WHERE id = ?""",
            (price, price, price, price, datetime.now().isoformat(), product_id)
        )
        is_new = False
    
    conn.commit()
    conn.close()
    return is_new


def record_price(product_id: str, price: float, source_page: str = "") -> Optional[Dict]:
    """记录一次价格，返回价格变化信息（如果有）"""
    conn = get_connection()
    cur = conn.cursor()
    
    # 获取上一个价格
    cur.execute(
        "SELECT price FROM price_history WHERE product_id=? ORDER BY scraped_at DESC LIMIT 1",
        (product_id,)
    )
    prev_row = cur.fetchone()
    prev_price = prev_row["price"] if prev_row else None
    
    # 插入新价格记录
    cur.execute(
        "INSERT INTO price_history (product_id, price, source_page) VALUES (?, ?, ?)",
        (product_id, price, source_page)
    )
    conn.commit()
    conn.close()
    
    if prev_price and prev_price != price:
        change_pct = round((price - prev_price) / prev_price * 100, 2)
        return {"prev": prev_price, "new": price, "change_pct": change_pct}
    return None


def record_alert(product_id: str, old_price: float, new_price: float, change_pct: float, alert_type: str):
    """记录一条告警"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO alerts (product_id, old_price, new_price, change_pct, alert_type) VALUES (?, ?, ?, ?, ?)",
        (product_id, old_price, new_price, change_pct, alert_type)
    )
    conn.commit()
    conn.close()


def mark_alert_notified(alert_id: int):
    conn = get_connection()
    conn.execute("UPDATE alerts SET notified=1 WHERE id=?", (alert_id,))
    conn.commit()
    conn.close()


def get_pending_alerts() -> List[Dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM alerts WHERE notified=0 ORDER BY created_at DESC LIMIT 20"
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_product_history(product_id: str, days: int = 30) -> List[Dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """SELECT price, scraped_at FROM price_history
           WHERE product_id=? AND scraped_at >= datetime('now', '-' || ? || ' days')
           ORDER BY scraped_at ASC""",
        (product_id, days)
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_products() -> List[Dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM products ORDER BY updated_at DESC")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_latest_price(product_id: str) -> Optional[float]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT price FROM price_history WHERE product_id=? ORDER BY scraped_at DESC LIMIT 1",
        (product_id,)
    )
    row = cur.fetchone()
    conn.close()
    return row["price"] if row else None


# 初始化
init_db()