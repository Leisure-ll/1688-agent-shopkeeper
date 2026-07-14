#!/usr/bin/env python3
"""Human approval store for write actions."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
import time
import uuid
from typing import Any, Dict, List, Optional


@dataclass
class ApprovalRequest:
    id: str
    action: str
    item_ids: List[str]
    shop_code: str
    status: str = "pending"
    created_at: float = field(default_factory=time.time)
    decided_at: float = 0.0
    result: Dict[str, Any] = field(default_factory=dict)


class ApprovalStore:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def create(self, action: str, item_ids: List[str], shop_code: str) -> ApprovalRequest:
        req = ApprovalRequest(
            id=f"approval_{uuid.uuid4().hex[:10]}",
            action=action,
            item_ids=item_ids,
            shop_code=shop_code,
        )
        self.save(req)
        return req

    def get(self, approval_id: str) -> Optional[ApprovalRequest]:
        path = self.root / f"{approval_id}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return ApprovalRequest(**data)

    def save(self, req: ApprovalRequest) -> None:
        path = self.root / f"{req.id}.json"
        path.write_text(json.dumps(asdict(req), ensure_ascii=False, indent=2), encoding="utf-8")

    def approve(self, approval_id: str, result: Dict[str, Any]) -> ApprovalRequest:
        req = self.get(approval_id)
        if not req:
            raise ValueError(f"approval not found: {approval_id}")
        req.status = "approved"
        req.decided_at = time.time()
        req.result = result
        self.save(req)
        return req
