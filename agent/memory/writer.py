from agent.memory.store import MemoryStore


class MemoryWriter:
    def __init__(self, store: MemoryStore):
        self.store = store

    def write(self, kind: str, content: str):
        self.store.append(kind, content)
        return {"ok": True}
