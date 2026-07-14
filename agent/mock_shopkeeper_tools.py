#!/usr/bin/env python3
"""SQLite-backed mock 1688 tools for local demos and agent evals."""

from __future__ import annotations

import json
from pathlib import Path
import sqlite3
from typing import Any, Dict, List


class MockShopkeeperTools:
    """A tiny local product database that mimics the remote 1688 data source."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def search_products(self, query: str, channel: str = "") -> Dict[str, Any]:
        tokens = [token for token in query.replace("，", " ").replace(",", " ").split() if token]
        rows = self._query_products(tokens, channel)
        products = [self._row_to_product(row) for row in rows]
        markdown = "未找到商品。" if not products else "\n".join(
            f"{idx}. {p['title']} - ¥{p['price']} ({p['id']})" for idx, p in enumerate(products, 1)
        )
        return {
            "success": bool(products),
            "markdown": markdown,
            "data": {"data_id": "mock_sqlite_search", "products": products, "query": query, "channel": channel},
        }

    def list_shops(self) -> Dict[str, Any]:
        with self._connect() as conn:
            rows = conn.execute(
                "select code, name, channel, is_authorized from shops order by id"
            ).fetchall()
        shops = [
            {"code": row["code"], "name": row["name"], "channel": row["channel"], "is_authorized": bool(row["is_authorized"])}
            for row in rows
        ]
        markdown = "未绑定店铺。" if not shops else "\n".join(
            f"- {shop['name']}（{shop['channel']}）code={shop['code']} 授权={'是' if shop['is_authorized'] else '否'}"
            for shop in shops
        )
        return {"success": True, "markdown": markdown, "data": {"shops": shops}}

    def publish_dry_run(self, item_ids: List[str], shop_code: str) -> Dict[str, Any]:
        if not item_ids:
            return {"success": False, "markdown": "没有可 dry-run 的商品。", "data": {"dry_run": True}}
        if not shop_code:
            return {"success": False, "markdown": "没有唯一可用店铺，无法 dry-run。", "data": {"dry_run": True}}

        with self._connect() as conn:
            shop = conn.execute(
                "select code, is_authorized from shops where code = ?",
                (shop_code,),
            ).fetchone()
            if not shop or not bool(shop["is_authorized"]):
                return {"success": False, "markdown": "目标店铺不存在或未授权。", "data": {"dry_run": True}}
            conn.execute(
                "insert into publish_runs(shop_code, item_ids, dry_run) values (?, ?, 1)",
                (shop_code, ",".join(item_ids)),
            )
            conn.commit()

        return {
            "success": True,
            "markdown": f"dry-run 通过：将提交 {len(item_ids)} 个商品到 {shop_code}，未执行真实写入。",
            "data": {"risk_level": "write", "dry_run": True, "origin_count": len(item_ids), "shop_code": shop_code},
        }

    def publish_real(self, item_ids: List[str], shop_code: str) -> Dict[str, Any]:
        if not item_ids or not shop_code:
            return {"success": False, "markdown": "缺少商品或店铺，无法正式铺货。", "data": {}}
        with self._connect() as conn:
            conn.execute(
                "insert into publish_runs(shop_code, item_ids, dry_run) values (?, ?, 0)",
                (shop_code, ",".join(item_ids)),
            )
            conn.commit()
        return {
            "success": True,
            "markdown": f"已模拟正式铺货：{len(item_ids)} 个商品 -> {shop_code}。",
            "data": {"dry_run": False, "submitted_count": len(item_ids), "shop_code": shop_code},
        }

    def product_detail(self, item_ids: str) -> Dict[str, Any]:
        ids = [item_id.strip() for item_id in item_ids.split(",") if item_id.strip()]
        if not ids:
            return {"success": False, "markdown": "没有 item_id。", "data": {}}
        placeholders = ",".join("?" for _ in ids)
        with self._connect() as conn:
            rows = conn.execute(
                f"select * from products where id in ({placeholders})",
                ids,
            ).fetchall()
        return {
            "success": bool(rows),
            "markdown": f"已读取 {len(rows)} 个 mock 商品详情。",
            "data": {"details": {row["id"]: self._row_to_product(row) for row in rows}},
        }

    def fetch_trend(self, query: str) -> Dict[str, Any]:
        return {"success": True, "markdown": f"{query} 近 30 天搜索热度上升，价格带集中在 39-59 元。", "data": {"query": query}}

    def fetch_opportunities(self) -> Dict[str, Any]:
        return {"success": True, "markdown": "mock 商机：夏季女装、收纳用品、户外防晒。", "data": {"topics": ["夏季女装"]}}

    def shop_daily(self) -> Dict[str, Any]:
        return {"success": True, "markdown": "mock 日报：动销稳定，建议补充夏季连衣裙测款。", "data": {"mode": "mock"}}

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                create table if not exists products (
                  id text primary key,
                  title text not null,
                  category text not null,
                  price real not null,
                  url text not null,
                  image text not null default '',
                  channel_tags text not null,
                  stats_json text not null
                );

                create table if not exists shops (
                  id integer primary key autoincrement,
                  code text unique not null,
                  name text not null,
                  channel text not null,
                  is_authorized integer not null
                );

                create table if not exists publish_runs (
                  id integer primary key autoincrement,
                  shop_code text not null,
                  item_ids text not null,
                  dry_run integer not null,
                  created_at datetime default current_timestamp
                );
                """
            )
            count = conn.execute("select count(*) as n from products").fetchone()["n"]
            if count == 0:
                self._seed(conn)
            conn.commit()

    def _seed(self, conn: sqlite3.Connection) -> None:
        products = [
            (
                "900000001",
                "夏季法式碎花连衣裙 一件代发",
                "女装/连衣裙",
                39.90,
                "https://detail.1688.com/offer/900000001.html",
                "",
                "douyin,xiaohongshu,taobao",
                {"last30DaysSales": 4120, "goodRates": 0.982, "repurchaseRate": 0.214, "collectionRate24h": 0.941, "downstreamOffer": 236},
            ),
            (
                "900000002",
                "小个子显瘦吊带连衣裙 抖音同款",
                "女装/连衣裙",
                45.80,
                "https://detail.1688.com/offer/900000002.html",
                "",
                "douyin,xiaohongshu",
                {"last30DaysSales": 2860, "goodRates": 0.976, "repurchaseRate": 0.188, "collectionRate24h": 0.912, "downstreamOffer": 128},
            ),
            (
                "900000003",
                "大码遮肉短袖连衣裙 直播供货",
                "女装/连衣裙",
                52.00,
                "https://detail.1688.com/offer/900000003.html",
                "",
                "douyin,taobao",
                {"last30DaysSales": 1930, "goodRates": 0.969, "repurchaseRate": 0.241, "collectionRate24h": 0.887, "downstreamOffer": 92},
            ),
            (
                "900000004",
                "桌面化妆品收纳盒 高颜值宿舍收纳",
                "家居/收纳",
                12.90,
                "https://detail.1688.com/offer/900000004.html",
                "",
                "xiaohongshu,taobao",
                {"last30DaysSales": 5300, "goodRates": 0.991, "repurchaseRate": 0.132, "collectionRate24h": 0.902, "downstreamOffer": 330},
            ),
        ]
        conn.executemany(
            """
            insert into products(id, title, category, price, url, image, channel_tags, stats_json)
            values (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [(p[0], p[1], p[2], p[3], p[4], p[5], p[6], json.dumps(p[7], ensure_ascii=False)) for p in products],
        )
        conn.execute(
            "insert into shops(code, name, channel, is_authorized) values (?, ?, ?, ?)",
            ("MOCK_DOUYIN_001", "面试演示抖店", "douyin", 1),
        )

    def _query_products(self, tokens: List[str], channel: str) -> List[sqlite3.Row]:
        sql = "select * from products"
        params: List[Any] = []
        clauses: List[str] = []
        if channel:
            clauses.append("channel_tags like ?")
            params.append(f"%{channel}%")
        if tokens:
            token_clauses = []
            for token in tokens:
                token_clauses.append("(title like ? or category like ?)")
                params.extend([f"%{token}%", f"%{token}%"])
            clauses.append("(" + " or ".join(token_clauses) + ")")
        if clauses:
            sql += " where " + " and ".join(clauses)
        sql += " limit 20"
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
            if not rows and tokens and channel:
                rows = conn.execute(
                    "select * from products where channel_tags like ? limit 20",
                    (f"%{channel}%",),
                ).fetchall()
            if not rows and tokens:
                rows = conn.execute("select * from products limit 20").fetchall()
        return sorted(rows, key=self._score_row, reverse=True)

    def _score_row(self, row: sqlite3.Row) -> float:
        stats = json.loads(row["stats_json"])
        return (
            float(stats.get("last30DaysSales") or 0) * 0.4
            + float(stats.get("goodRates") or 0) * 100
            + float(stats.get("repurchaseRate") or 0) * 80
            + float(stats.get("collectionRate24h") or 0) * 50
        )

    def _row_to_product(self, row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "title": row["title"],
            "category": row["category"],
            "price": f"{float(row['price']):.2f}",
            "url": row["url"],
            "image": row["image"],
            "stats": json.loads(row["stats_json"]),
        }


_default_tools = MockShopkeeperTools(Path(".agent_data_mock") / "mock_catalog.sqlite")


def search_products(query: str, channel: str = "") -> Dict[str, Any]:
    return _default_tools.search_products(query, channel)


def list_shops() -> Dict[str, Any]:
    return _default_tools.list_shops()


def publish_dry_run(item_ids: List[str], shop_code: str) -> Dict[str, Any]:
    return _default_tools.publish_dry_run(item_ids, shop_code)


def publish_real(item_ids: List[str], shop_code: str) -> Dict[str, Any]:
    return _default_tools.publish_real(item_ids, shop_code)


def product_detail(item_ids: str) -> Dict[str, Any]:
    return _default_tools.product_detail(item_ids)


def fetch_trend(query: str) -> Dict[str, Any]:
    return _default_tools.fetch_trend(query)


def fetch_opportunities() -> Dict[str, Any]:
    return _default_tools.fetch_opportunities()


def shop_daily() -> Dict[str, Any]:
    return _default_tools.shop_daily()
