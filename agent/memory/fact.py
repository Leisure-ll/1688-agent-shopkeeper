from dataclasses import dataclass
from typing import Dict


@dataclass
class MemoryFact:
    key: str
    value: str
    kind: str
    confidence: float = 1.0

    def to_memory_text(self) -> str:
        return f"- key: {self.key}\n  value: {self.value}\n  confidence: {self.confidence:.2f}"

    def to_graph_event(self, action: str) -> Dict[str, object]:
        return {
            "type": "memory_fact",
            "action": action,
            "key": self.key,
            "value": self.value,
            "kind": self.kind,
            "confidence": self.confidence,
        }
