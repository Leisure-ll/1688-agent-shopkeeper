from typing import Dict

from agent.memory.compressor import MemoryCompressor
from agent.memory.conflict import MemoryConflictDetector
from agent.memory.dedup import MemoryDeduper
from agent.memory.dream import MemoryDreamer
from agent.memory.extractor import MemoryExtractor
from agent.memory.store import MemoryStore


class MemoryPipeline:
    def __init__(self, store: MemoryStore):
        self.store = store
        self.extractor = MemoryExtractor()
        self.compressor = MemoryCompressor()
        self.deduper = MemoryDeduper(store)
        self.conflicts = MemoryConflictDetector(store)
        self.dreamer = MemoryDreamer()

    def write(self, kind: str, content: str) -> Dict[str, object]:
        raw_facts = self.extractor.extract(kind, content)
        for fact in raw_facts:
            fact.value = self.compressor.compress(fact.value)
        facts = self.deduper.dedup(raw_facts)
        accepted, conflicts = self.conflicts.split_conflicts(facts)
        for fact in accepted:
            self.store.append(kind, fact.to_memory_text())
            self.store.export_graph_event(fact.to_graph_event("upsert"))
        for fact in conflicts:
            self.store.export_graph_event(fact.to_graph_event("conflict"))
        reflection = self.dreamer.reflect(accepted)
        if reflection:
            self.store.append("reflection", reflection)
            self.store.export_graph_event({"type": "memory_reflection", "action": "append", "content": reflection})
        return {
            "ok": True,
            "extracted": len(raw_facts),
            "deduped": len(raw_facts) - len(facts),
            "written": len(accepted),
            "conflicts": len(conflicts),
            "reflected": bool(reflection),
        }
