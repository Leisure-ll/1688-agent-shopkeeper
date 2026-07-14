from typing import Dict, List

from agent.memory.store import MemoryStore


class MemoryRetriever:
    def __init__(self, store: MemoryStore):
        self.store = store

    def retrieve(self, query: str, limit: int = 5) -> List[Dict[str, str]]:
        return self.store.search(query, limit)
