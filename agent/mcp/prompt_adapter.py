from typing import Dict, List

from agent.prompts.registry import PromptRegistry


class MCPPromptAdapter:
    def __init__(self, registry: PromptRegistry = None):
        self.registry = registry or PromptRegistry()

    def list_prompts(self) -> List[Dict[str, str]]:
        return [self.registry.load(name) for name in ["planner", "memory", "reviewer"]]
