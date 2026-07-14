from typing import Dict, List

from agent.memory.store import MemoryStore
from agent.persist.plan_store import PlanStore


class MCPResourceAdapter:
    def __init__(self, store: PlanStore, memory: MemoryStore):
        self.store = store
        self.memory = memory

    def list_resources(self) -> List[Dict[str, str]]:
        return [
            {"uri": "memory://MEMORY.md", "name": "Long-term memory"},
            {"uri": "memory://graph", "name": "Memory graph events"},
            {"uri": "plans://", "name": "Plan store"},
        ]

    def read_resource(self, uri: str) -> Dict[str, object]:
        if uri == "memory://MEMORY.md":
            return {"uri": uri, "text": self.memory.memory_md.read_text(encoding="utf-8")}
        if uri == "memory://graph":
            return {"uri": uri, "events": self.memory.graph.query(limit=100)}
        raise KeyError(f"unknown resource uri: {uri}")
