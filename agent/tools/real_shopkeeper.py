import sys
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


class RealShopkeeperTools:
    def search_products(self, query: str, channel: str = "douyin", limit: int = 5) -> Dict[str, Any]:
        from capabilities.search.service import product_to_dict, search_products

        products = search_products(query, channel)[:limit]
        return {"products": [product_to_dict(p) for p in products]}

    def list_shops(self, channel: str = "douyin") -> Dict[str, Any]:
        from capabilities.shops.service import list_shops

        return {"shops": list_shops(channel)}

    def publish_dry_run(self, product_ids: List[str], shop_id: str = "") -> Dict[str, Any]:
        return {"mode": "dry_run", "shop_id": shop_id, "product_ids": product_ids, "ok": True}

    def publish_real(self, product_ids: List[str], shop_id: str = "") -> Dict[str, Any]:
        from capabilities.publish.service import publish_products

        return publish_products(product_ids, shop_id)
