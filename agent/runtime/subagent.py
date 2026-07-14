import json
from pathlib import Path
from typing import Any, Dict, Iterable

from agent.core.hooks import AgentEventHooks
from agent.core.state import Task, new_id
from agent.tools.registry import ToolRegistry


class SubAgent:
    def __init__(self, role: str, registry: ToolRegistry, allowed_tools: Iterable[str], workspace: str, hooks: AgentEventHooks):
        self.id = new_id("subagent")
        self.role = role
        self.registry = registry
        self.allowed_tools = set(allowed_tools)
        self.trace_path = Path(workspace) / "subagents" / f"{self.id}.json"
        self.trace_path.parent.mkdir(parents=True, exist_ok=True)
        self.hooks = hooks
        self.hooks.on_subagent_spawned(subagent_id=self.id, role=role, allowed_tools=sorted(self.allowed_tools))

    def run_tool(self, task: Task, args: Dict[str, Any]) -> Dict[str, Any]:
        self.hooks.on_tool_start(subagent_id=self.id, tool=task.tool, task_id=task.id, args=args)
        try:
            result = self.registry.call(task.tool, self.allowed_tools, **args)
            error = None
            return result
        except Exception as exc:
            result = {"error": str(exc)}
            error = str(exc)
            raise
        finally:
            payload = {"subagent_id": self.id, "role": self.role, "task": task.__dict__, "args": args, "result": locals().get("result")}
            self.trace_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            self.hooks.on_tool_end(subagent_id=self.id, tool=task.tool, task_id=task.id, error=locals().get("error"))
