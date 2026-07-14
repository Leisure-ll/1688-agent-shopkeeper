from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List


@dataclass
class Tool:
    name: str
    func: Callable[..., Dict[str, Any]]
    description: str = ""


class ToolRegistry:
    def __init__(self):
        self.tools: Dict[str, Tool] = {}

    def register(self, name: str, func: Callable[..., Dict[str, Any]], description: str = "") -> None:
        self.tools[name] = Tool(name, func, description)

    def call(self, name: str, allowed: Iterable[str], **kwargs: Any) -> Dict[str, Any]:
        if name not in set(allowed):
            raise PermissionError(f"tool {name} is not allowed in current context")
        if name not in self.tools:
            raise KeyError(f"tool {name} is not registered")
        return self.tools[name].func(**kwargs)

    def names(self) -> List[str]:
        return sorted(self.tools)
