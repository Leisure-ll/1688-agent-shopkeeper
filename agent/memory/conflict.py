from typing import Iterable, List, Tuple

from agent.memory.fact import MemoryFact
from agent.memory.store import MemoryStore


class MemoryConflictDetector:
    def __init__(self, store: MemoryStore):
        self.store = store

    def split_conflicts(self, facts: Iterable[MemoryFact]) -> Tuple[List[MemoryFact], List[MemoryFact]]:
        existing = self.store.memory_md.read_text(encoding="utf-8")
        accepted: List[MemoryFact] = []
        conflicts: List[MemoryFact] = []
        for fact in facts:
            marker = f"key: {fact.key}"
            if marker in existing and fact.value not in existing:
                conflicts.append(fact)
            else:
                accepted.append(fact)
        return accepted, conflicts
