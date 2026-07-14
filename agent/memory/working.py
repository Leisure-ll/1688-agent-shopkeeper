from collections import deque
from typing import Deque, Dict, List


class WorkingMemory:
    def __init__(self, max_items: int = 20):
        self.max_items = max_items
        self.items: Deque[Dict[str, str]] = deque(maxlen=max_items)

    def add(self, kind: str, content: str) -> None:
        self.items.append({"kind": kind, "content": content})

    def context(self, limit: int = 8) -> List[Dict[str, str]]:
        return list(self.items)[-limit:]

    def clear(self) -> None:
        self.items.clear()
