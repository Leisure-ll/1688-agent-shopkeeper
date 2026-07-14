#!/usr/bin/env python3
"""Tool wrappers around the existing 1688 capability services."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from _errors import SkillError  # noqa: E402
from capabilities.opportunities.service import fetch_opportunities as _fetch_opportunities  # noqa: E402
from capabilities.prod_detail.service import fetch_and_save_product_details as _fetch_product_details  # noqa: E402
from capabilities.publish.service import publish_with_check  # noqa: E402
from capabilities.search.service import product_to_dict, search_and_save  # noqa: E402
from capabilities.shops.service import list_bound_shops  # noqa: E402
from capabilities.shop_daily.service import fetch_shop_daily as _fetch_shop_daily  # noqa: E402
from capabilities.trend.service import fetch_trend as _fetch_trend  # noqa: E402


def _safe_call(fn, **kwargs: Any) -> Dict[str, Any]:
    try:
        return fn(**kwargs)
    except SkillError as exc:
        return {"success": False, "markdown": f"❌ {exc.message}", "data": {"error": exc.message}}
    except Exception as exc:
        return {"success": False, "markdown": f"❌ 工具执行失败：{exc}", "data": {"error": str(exc)}}


def search_products(query: str, channel: str = "") -> Dict[str, Any]:
    def run() -> Dict[str, Any]:
        result = search_and_save(query=query, channel=channel)
        products = [product_to_dict(p) for p in result.get("products", [])]
        return {
            "success": bool(products),
            "markdown": result.get("markdown", ""),
            "data": {
                "data_id": result.get("data_id", ""),
                "products": products,
                "query": query,
                "channel": channel,
            },
        }

    return _safe_call(run)


def product_detail(item_ids: str) -> Dict[str, Any]:
    def run() -> Dict[str, Any]:
        ids = [item_id.strip() for item_id in item_ids.split(",") if item_id.strip()]
        result = _fetch_product_details(ids)
        return {"success": True, "markdown": result.get("markdown", ""), "data": result}

    return _safe_call(run)


def list_shops() -> Dict[str, Any]:
    def run() -> Dict[str, Any]:
        shops = list_bound_shops()
        rows: List[Dict[str, Any]] = []
        for shop in shops:
            rows.append(
                {
                    "code": shop.code,
                    "name": shop.name,
                    "channel": shop.channel,
                    "is_authorized": shop.is_authorized,
                }
            )
        markdown = "未绑定店铺。" if not rows else "\n".join(
            f"- {row['name']}（{row['channel']}）code={row['code']} 授权={'是' if row['is_authorized'] else '否'}"
            for row in rows
        )
        return {"success": True, "markdown": markdown, "data": {"shops": rows}}

    return _safe_call(run)


def fetch_trend(query: str) -> Dict[str, Any]:
    def run() -> Dict[str, Any]:
        result = _fetch_trend(query)
        return {"success": True, "markdown": result.get("markdown", ""), "data": result.get("data", {})}

    return _safe_call(run)


def fetch_opportunities() -> Dict[str, Any]:
    def run() -> Dict[str, Any]:
        result = _fetch_opportunities()
        return {"success": True, "markdown": result.get("markdown", ""), "data": result.get("data", {})}

    return _safe_call(run)


def shop_daily() -> Dict[str, Any]:
    def run() -> Dict[str, Any]:
        result = _fetch_shop_daily()
        return {"success": True, "markdown": result.get("markdown", ""), "data": result.get("data", {})}

    return _safe_call(run)


def publish_dry_run(item_ids: List[str], shop_code: str) -> Dict[str, Any]:
    def run() -> Dict[str, Any]:
        result = publish_with_check(item_ids=item_ids, shop_code=shop_code, dry_run=True)
        return {
            "success": result["success"],
            "markdown": result["markdown"],
            "data": {
                "risk_level": "write",
                "dry_run": True,
                "origin_count": result["origin_count"],
            },
        }

    return _safe_call(run)


def publish_real(item_ids: List[str], shop_code: str) -> Dict[str, Any]:
    def run() -> Dict[str, Any]:
        result = publish_with_check(item_ids=item_ids, shop_code=shop_code, dry_run=False)
        return {
            "success": result["success"],
            "markdown": result["markdown"],
            "data": {
                "risk_level": "write",
                "dry_run": False,
                "origin_count": result["origin_count"],
            },
        }

    return _safe_call(run)
