import json
from pathlib import Path
from typing import Dict, List

from agent.core.state import new_id


class ApprovalStore:
    def __init__(self, workspace: str = ".agent_data"):
        self.root = Path(workspace) / "approvals"
        self.root.mkdir(parents=True, exist_ok=True)

    def request_publish(self, product_ids: List[str], shop_id: str = "s1") -> Dict[str, object]:
        approval_id = new_id("approval")
        payload = {"id": approval_id, "type": "publish_real", "product_ids": product_ids, "shop_id": shop_id, "status": "pending"}
        (self.root / f"{approval_id}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return payload

    def approve(self, approval_id: str) -> Dict[str, object]:
        path = self.root / f"{approval_id}.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["status"] = "approved"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return payload
