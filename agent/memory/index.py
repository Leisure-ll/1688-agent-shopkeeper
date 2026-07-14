import re
import sqlite3
from pathlib import Path
from typing import List


class MemoryIndex:
    def __init__(self, index_path: Path, memory_md: Path):
        self.index_path = index_path
        self.memory_md = memory_md

    def rebuild(self) -> int:
        text = self.memory_md.read_text(encoding="utf-8") if self.memory_md.exists() else ""
        blocks = [block.strip() for block in re.split(r"\n## ", text) if block.strip() and not block.startswith("#")]
        with sqlite3.connect(str(self.index_path)) as conn:
            conn.execute("delete from memories")
            for block in blocks:
                header, _, content = block.partition("\n")
                parts = header.split(maxsplit=1)
                ts = parts[0] if parts else ""
                kind = parts[1] if len(parts) > 1 else "unknown"
                conn.execute("insert into memories(ts, kind, content) values (?, ?, ?)", (ts, kind, content.strip()))
        return len(blocks)

    def keys(self) -> List[str]:
        if not self.memory_md.exists():
            return []
        return re.findall(r"key:\s*([^\n]+)", self.memory_md.read_text(encoding="utf-8"))
