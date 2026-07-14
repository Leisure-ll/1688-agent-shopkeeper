from typing import Dict

from agent.memory.store import MemoryStore
from agent.persist.plan_store import PlanStore


class RuntimeTools:
    def __init__(self, store: PlanStore, memory: MemoryStore):
        self.store = store
        self.memory = memory

    def get_plan_status(self, plan_id: str) -> Dict[str, object]:
        plan = self.store.load(plan_id)
        return {
            "plan_id": plan.id,
            "status": plan.status,
            "version": plan.version,
            "tasks": [{"id": task.id, "title": task.title, "status": task.status, "tool": task.tool} for task in plan.tasks],
        }

    def list_checkpoints(self, plan_id: str) -> Dict[str, object]:
        return {"plan_id": plan_id, "checkpoints": self.store.list_checkpoints(plan_id)}

    def get_memory_graph(self, key: str = "", action: str = "", limit: int = 20) -> Dict[str, object]:
        return {"events": self.memory.graph.query(key=key, action=action, limit=limit)}
