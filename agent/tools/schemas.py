from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class ToolCallSpec:
    name: str
    args: Dict[str, Any] = field(default_factory=dict)
    risk: str = "read"
