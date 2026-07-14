from typing import Dict

from agent.mcp.prompt_adapter import MCPPromptAdapter
from agent.mcp.resource_adapter import MCPResourceAdapter
from agent.mcp.tool_adapter import MCPToolAdapter
from agent.runtime.app import AgentRuntime


class MCPServerDescription:
    def __init__(self, runtime: AgentRuntime):
        self.runtime = runtime

    def describe(self) -> Dict[str, object]:
        return {
            "name": "1688-agent-shopkeeper",
            "tools": MCPToolAdapter(self.runtime.registry).list_tools(),
            "resources": MCPResourceAdapter(self.runtime.store, self.runtime.memory).list_resources(),
            "prompts": MCPPromptAdapter().list_prompts(),
        }
