#!/usr/bin/env python3
"""Long-term memory with MEMORY.md as the authoritative source."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import sqlite3
import time
from typing import Dict, List, Tuple, Union


@dataclass
class MemoryItem:
    section: str
    key: str
    value: str
    confidence: float = 1.0
    updated_at: float = time.time()

    def to_markdown_line(self) -> str:
        meta = json.dumps(
            {"confidence": self.confidence, "updated_at": self.updated_at},
            ensure_ascii=False,
            separators=(",", ":"),
        )
        return f"- **{self.key}**: {self.value} <!-- {meta} -->"


class LongTermMemory:
    """Stores facts in MEMORY.md and builds a lightweight keyword index from it.

    MEMORY.md is the only source of truth. The index is rebuilt from the file,
    which mirrors the Kugelblitz design where vector DBs are derived indexes.
    """

    def __init__(self, memory_path: Union[str, Path], graph_path: Union[str, Path]):
        self.memory_path = Path(memory_path)
        self.graph_path = Path(graph_path)
        self.index_path = self.memory_path.parent / "memory_index.sqlite"
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        self.graph_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.memory_path.exists():
            self.memory_path.write_text("# Project Memory\n\n", encoding="utf-8")
        self._items: List[MemoryItem] = []
        self.rebuild_index()

    def rebuild_index(self) -> None:
        self._items = self._parse_memory()
        self._rebuild_sqlite_index()

    def _parse_memory(self) -> List[MemoryItem]:
        current_section = ""
        items: List[MemoryItem] = []
        for line in self.memory_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("## "):
                current_section = line[3:].strip()
                continue
            match = re.match(r"- \*\*(.+?)\*\*: (.*?)(?: <!-- (.+) -->)?$", line)
            if not match or not current_section:
                continue
            key, value, raw_meta = match.groups()
            confidence = 1.0
            updated_at = time.time()
            if raw_meta:
                try:
                    meta = json.loads(raw_meta)
                    confidence = float(meta.get("confidence", confidence))
                    updated_at = float(meta.get("updated_at", updated_at))
                except Exception:
                    pass
            items.append(MemoryItem(current_section, key, value, confidence, updated_at))
        return items

    def store(self, section: str, key: str, value: str, confidence: float = 1.0) -> MemoryItem:
        item = MemoryItem(section=section, key=key, value=value, confidence=confidence, updated_at=time.time())
        items = [old for old in self._items if not (old.section == section and old.key == key)]
        items.append(item)
        self._write(items)
        self._items = items
        self._rebuild_sqlite_index()
        self._append_graph_hint(section, key, value)
        return item

    def search(self, query: str, limit: int = 5) -> List[MemoryItem]:
        indexed = self._search_sqlite_index(query, limit)
        if indexed:
            return indexed
        terms = {term.lower() for term in re.findall(r"[\w\u4e00-\u9fff]+", query)}
        scored: List[Tuple[int, MemoryItem]] = []
        for item in self._items:
            haystack = f"{item.section} {item.key} {item.value}".lower()
            score = sum(1 for term in terms if term and term in haystack)
            if score:
                scored.append((score, item))
        return [item for _, item in sorted(scored, key=lambda pair: pair[0], reverse=True)[:limit]]

    def sections(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for item in self._items:
            counts[item.section] = counts.get(item.section, 0) + 1
        return counts

    def _write(self, items: List[MemoryItem]) -> None:
        grouped: Dict[str, List[MemoryItem]] = {}
        for item in items:
            grouped.setdefault(item.section, []).append(item)

        lines = ["# Project Memory", ""]
        for section in sorted(grouped):
            lines.append(f"## {section}")
            for item in sorted(grouped[section], key=lambda x: x.key):
                lines.append(item.to_markdown_line())
            lines.append("")
        self.memory_path.write_text("\n".join(lines), encoding="utf-8")

    def _append_graph_hint(self, section: str, key: str, value: str) -> None:
        record = {
            "type": "memory_fact",
            "section": section,
            "key": key,
            "value": value,
            "updated_at": time.time(),
        }
        with self.graph_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _rebuild_sqlite_index(self) -> None:
        with sqlite3.connect(str(self.index_path)) as conn:
            conn.execute(
                """
                create table if not exists memory_index (
                  section text not null,
                  key text not null,
                  value text not null,
                  confidence real not null,
                  updated_at real not null,
                  search_text text not null,
                  primary key(section, key)
                )
                """
            )
            conn.execute("delete from memory_index")
            conn.executemany(
                """
                insert into memory_index(section, key, value, confidence, updated_at, search_text)
                values (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        item.section,
                        item.key,
                        item.value,
                        item.confidence,
                        item.updated_at,
                        f"{item.section} {item.key} {item.value}".lower(),
                    )
                    for item in self._items
                ],
            )
            conn.commit()

    def _search_sqlite_index(self, query: str, limit: int) -> List[MemoryItem]:
        terms = [term.lower() for term in re.findall(r"[\w\u4e00-\u9fff]+", query) if term]
        if not terms or not self.index_path.exists():
            return []
        where = " or ".join("search_text like ?" for _ in terms)
        params = [f"%{term}%" for term in terms]
        with sqlite3.connect(str(self.index_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                f"select * from memory_index where {where} order by updated_at desc limit ?",
                params + [limit],
            ).fetchall()
        return [
            MemoryItem(
                section=row["section"],
                key=row["key"],
                value=row["value"],
                confidence=float(row["confidence"]),
                updated_at=float(row["updated_at"]),
            )
            for row in rows
        ]
