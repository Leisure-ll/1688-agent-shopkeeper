from agent.memory.pipeline import MemoryPipeline
from agent.memory.store import MemoryStore


class MemoryWriter:
    def __init__(self, store: MemoryStore):
        self.store = store
        self.pipeline = MemoryPipeline(store)

    def write(self, kind: str, content: str):
        return self.pipeline.write(kind, content)
