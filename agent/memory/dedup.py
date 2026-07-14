from typing import Iterable, List

from agent.memory.fact import MemoryFact
from agent.memory.store import MemoryStore


class MemoryDeduper:
    def __init__(self, store: MemoryStore):
        self.store = store

    def dedup(self, facts: Iterable[MemoryFact]) -> List[MemoryFact]:
        existing = self.store.memory_md.read_text(encoding="utf-8")
        return [fact for fact in facts if f"key: {fact.key}" not in existing]
