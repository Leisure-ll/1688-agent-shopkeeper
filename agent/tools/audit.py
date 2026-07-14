import json
from datetime import datetime
from pathlib import Path
from typing import Dict


class ToolAuditLog:
    def __init__(self, workspace: str):
        self.path = Path(workspace) / "observability" / "tool_audit.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, event: Dict[str, object]) -> None:
        row = {"ts": datetime.utcnow().isoformat() + "Z", **event}
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
