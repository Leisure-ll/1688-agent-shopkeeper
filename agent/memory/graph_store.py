import json
from pathlib import Path
from typing import Dict, List


class MemoryGraphStore:
    def __init__(self, root: Path):
        self.path = root / "memory_graph.jsonl"

    def append(self, event: Dict[str, object]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False) + "\n")

    def query(self, key: str = "", action: str = "", limit: int = 20) -> List[Dict[str, object]]:
        if not self.path.exists():
            return []
        rows: List[Dict[str, object]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            event = json.loads(line)
            if key and event.get("key") != key:
                continue
            if action and event.get("action") != action:
                continue
            rows.append(event)
            if len(rows) >= limit:
                break
        return rows
