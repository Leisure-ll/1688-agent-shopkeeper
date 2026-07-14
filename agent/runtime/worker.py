from typing import Dict, List

from agent.core.hooks import AgentEventHooks
from agent.core.state import Task
from agent.runtime.subagent import SubAgent
from agent.tools.policy import allowed_for_worker
from agent.tools.registry import ToolRegistry


class DeterministicWorkerPolicy:
    def role_for(self, task: Task) -> str:
        if task.tool in {"search_products", "memory_search"}:
            return "selector"
        if task.tool == "list_shops":
            return "shop"
        if task.tool in {"publish_dry_run", "request_publish_approval"}:
            return "publisher"
        return "advisor"

    def args_for(self, task: Task, context: Dict[str, object]) -> Dict[str, object]:
        args = dict(task.args)
        if task.tool in {"publish_dry_run", "request_publish_approval"}:
            products: List[dict] = context.get("products", [])  # type: ignore[assignment]
            shops: List[dict] = context.get("shops", [])  # type: ignore[assignment]
            args.setdefault("product_ids", [p.get("id") for p in products[:5]])
            args.setdefault("shop_id", shops[0].get("id") if shops else "s1")
        if task.tool == "write_memory":
            products = context.get("products", [])
            args.setdefault("content", f"Recent selected products: {products}")
        return args


class AgentWorker:
    def __init__(self, registry: ToolRegistry, workspace: str, hooks: AgentEventHooks, policy: DeterministicWorkerPolicy = None):
        self.registry = registry
        self.workspace = workspace
        self.hooks = hooks
        self.policy = policy or DeterministicWorkerPolicy()

    def run(self, task: Task, context: Dict[str, object]) -> Dict[str, object]:
        role = self.policy.role_for(task)
        subagent = SubAgent(role, self.registry, allowed_for_worker(role), self.workspace, self.hooks)
        result = subagent.run_tool(task, self.policy.args_for(task, context))
        if "products" in result:
            context["products"] = result["products"]
        if "shops" in result:
            context["shops"] = result["shops"]
        return result
