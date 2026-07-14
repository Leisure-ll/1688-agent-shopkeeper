import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List


class MemoryStore:
    """MEMORY.md is the source of truth; SQLite is a derived retrieval index."""

    def __init__(self, workspace: str = ".agent_data"):
        self.root = Path(workspace) / "memory"
        self.root.mkdir(parents=True, exist_ok=True)
        self.memory_md = self.root / "MEMORY.md"
        self.index = self.root / "memory_index.sqlite"
        if not self.memory_md.exists():
            self.memory_md.write_text("# Long Term Memory\n\n", encoding="utf-8")
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(str(self.index)) as conn:
            conn.execute(
                "create table if not exists memories "
                "(id integer primary key autoincrement, ts text, kind text, content text)"
            )

    def append(self, kind: str, content: str) -> None:
        ts = datetime.utcnow().isoformat() + "Z"
        with self.memory_md.open("a", encoding="utf-8") as fh:
            fh.write(f"\n## {ts} {kind}\n\n{content}\n")
        with sqlite3.connect(str(self.index)) as conn:
            conn.execute(
                "insert into memories(ts, kind, content) values (?, ?, ?)",
                (ts, kind, content),
            )

    def search(self, query: str, limit: int = 5) -> List[Dict[str, str]]:
        words = [word for word in query.lower().split() if word]
        sql = "select ts, kind, content from memories order by id desc"
        rows: List[Dict[str, str]] = []
        with sqlite3.connect(str(self.index)) as conn:
            for ts, kind, content in conn.execute(sql):
                text = content.lower()
                if not words or any(word in text for word in words):
                    rows.append({"ts": ts, "kind": kind, "content": content})
                if len(rows) >= limit:
                    break
        return rows

    def export_graph_event(self, event: Dict[str, object]) -> None:
        path = self.root / "memory_graph.jsonl"
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False) + "\n")
