from typing import Dict, List

from agent.tools.registry import ToolRegistry
from agent.tools.risk import classify_tool_risk


class MCPToolAdapter:
    def __init__(self, registry: ToolRegistry):
        self.registry = registry

    def list_tools(self) -> List[Dict[str, object]]:
        return [
            {
                "name": name,
                "description": self.registry.tools[name].description,
                "risk": classify_tool_risk(name),
            }
            for name in self.registry.names()
        ]
