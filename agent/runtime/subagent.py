import json
from pathlib import Path
from typing import Any, Dict, Iterable

from agent.core.hooks import AgentEventHooks
from agent.core.state import Task, new_id
from agent.tools.audit import ToolAuditLog
from agent.tools.registry import ToolRegistry
from agent.tools.risk import classify_tool_risk


class SubAgent:
    def __init__(self, role: str, registry: ToolRegistry, allowed_tools: Iterable[str], workspace: str, hooks: AgentEventHooks):
        self.id = new_id("subagent")
        self.role = role
        self.registry = registry
        self.allowed_tools = set(allowed_tools)
        self.trace_path = Path(workspace) / "subagents" / f"{self.id}.json"
        self.trace_path.parent.mkdir(parents=True, exist_ok=True)
        self.hooks = hooks
        self.audit = ToolAuditLog(workspace)
        self.hooks.on_subagent_spawned(subagent_id=self.id, role=role, allowed_tools=sorted(self.allowed_tools))

    def run_tool(self, task: Task, args: Dict[str, Any]) -> Dict[str, Any]:
        risk = classify_tool_risk(task.tool)
        self.audit.append({"event": "tool.start", "subagent_id": self.id, "role": self.role, "tool": task.tool, "risk": risk, "task_id": task.id})
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
            self.audit.append({"event": "tool.end", "subagent_id": self.id, "role": self.role, "tool": task.tool, "risk": risk, "task_id": task.id, "error": locals().get("error")})
            self.hooks.on_tool_end(subagent_id=self.id, tool=task.tool, task_id=task.id, error=locals().get("error"))
