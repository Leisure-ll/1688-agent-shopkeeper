import sqlite3
from pathlib import Path
from typing import Any, Dict, List


class MockShopkeeperDB:
    def __init__(self, workspace: str = ".agent_data"):
        self.path = Path(workspace) / "mock_catalog.sqlite"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _init(self) -> None:
        with sqlite3.connect(str(self.path)) as conn:
            conn.execute(
                "create table if not exists products "
                "(id text primary key, title text, category text, price real, sales integer, rating real, supplier_score real)"
            )
            conn.execute(
                "create table if not exists shops "
                "(id text primary key, name text, channel text, status text)"
            )
            conn.execute(
                "create table if not exists publish_runs "
                "(id integer primary key autoincrement, product_id text, shop_id text, mode text)"
            )
            if conn.execute("select count(*) from products").fetchone()[0] == 0:
                rows = [
                    ("p1001", "法式碎花雪纺连衣裙", "夏季连衣裙", 69.0, 4300, 4.8, 92),
                    ("p1002", "通勤收腰A字连衣裙", "夏季连衣裙", 89.0, 3100, 4.7, 89),
                    ("p1003", "小个子方领泡泡袖裙", "夏季连衣裙", 59.0, 5200, 4.6, 86),
                    ("p1004", "纯色吊带内搭连衣裙", "夏季连衣裙", 39.0, 8000, 4.5, 84),
                    ("p1005", "新中式改良盘扣裙", "夏季连衣裙", 109.0, 1800, 4.9, 95),
                    ("p2001", "冰丝防晒开衫", "夏季女装", 29.0, 12000, 4.4, 81),
                ]
                conn.executemany("insert into products values (?, ?, ?, ?, ?, ?, ?)", rows)
            if conn.execute("select count(*) from shops").fetchone()[0] == 0:
                conn.executemany(
                    "insert into shops values (?, ?, ?, ?)",
                    [("s1", "抖店女装一店", "douyin", "active"), ("s2", "小红书穿搭店", "xiaohongshu", "active")],
                )


def _rows(conn: sqlite3.Connection, sql: str, args: tuple = ()) -> List[Dict[str, Any]]:
    conn.row_factory = sqlite3.Row
    return [dict(row) for row in conn.execute(sql, args).fetchall()]


class MockShopkeeperTools:
    def __init__(self, workspace: str = ".agent_data"):
        self.db = MockShopkeeperDB(workspace)

    def search_products(self, query: str, channel: str = "", limit: int = 5) -> Dict[str, Any]:
        keyword = "连衣裙" if "裙" in query else query
        with sqlite3.connect(str(self.db.path)) as conn:
            products = _rows(
                conn,
                "select * from products where title like ? or category like ? order by sales desc limit ?",
                (f"%{keyword}%", f"%{keyword}%", limit),
            )
        for p in products:
            p["score"] = round(p["sales"] / 1000 + p["rating"] * 10 + p["supplier_score"] / 10, 2)
        return {"products": products}

    def list_shops(self, channel: str = "douyin") -> Dict[str, Any]:
        with sqlite3.connect(str(self.db.path)) as conn:
            shops = _rows(conn, "select * from shops where channel = ? and status = 'active'", (channel,))
        return {"shops": shops}

    def publish_dry_run(self, product_ids: List[str], shop_id: str = "s1") -> Dict[str, Any]:
        return {"mode": "dry_run", "shop_id": shop_id, "product_ids": product_ids, "ok": True}

    def publish_real(self, product_ids: List[str], shop_id: str = "s1") -> Dict[str, Any]:
        with sqlite3.connect(str(self.db.path)) as conn:
            conn.executemany(
                "insert into publish_runs(product_id, shop_id, mode) values (?, ?, 'real')",
                [(pid, shop_id) for pid in product_ids],
            )
        return {"mode": "real", "shop_id": shop_id, "product_ids": product_ids, "ok": True}
