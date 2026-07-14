import json
from typing import Any, Dict, List, Protocol

from agent.core.state import Plan, Task, new_id


class JSONPlannerProvider(Protocol):
    def create_plan(self, goal: str, memories: List[Dict[str, str]]) -> Dict[str, Any]:
        ...


class HeuristicPlanner:
    def create_plan(self, goal: str, memories: List[Dict[str, str]] = None) -> Plan:
        formal_publish = any(word in goal for word in ["正式铺货", "确认铺货", "真的铺货", "执行铺货"])
        query = goal
        tasks = [
            Task(new_id("task"), "检索历史经营记忆", "memory_search", {"query": goal}),
            Task(new_id("task"), "搜索候选商品", "search_products", {"query": query, "channel": "douyin", "limit": 5}),
            Task(new_id("task"), "查询可用店铺", "list_shops", {"channel": "douyin"}),
        ]
        publish_tool = "request_publish_approval" if formal_publish else "publish_dry_run"
        tasks.append(Task(new_id("task"), "铺货预检查" if not formal_publish else "申请正式铺货审批", publish_tool, {}))
        tasks.append(Task(new_id("task"), "沉淀选品决策记忆", "write_memory", {"kind": "selection"}))
        return Plan(id=new_id("plan"), goal=goal, status="init", tasks=tasks, notes=["heuristic planner"])


class LLMPlanner:
    def __init__(self, provider: JSONPlannerProvider):
        self.provider = provider

    def create_plan(self, goal: str, memories: List[Dict[str, str]] = None) -> Plan:
        data = self.provider.create_plan(goal, memories or [])
        tasks = [
            Task(
                id=item.get("id") or new_id("task"),
                title=item["title"],
                tool=item["tool"],
                args=item.get("args", {}),
                depends_on=item.get("depends_on", []),
            )
            for item in data["tasks"]
        ]
        return Plan(id=data.get("id") or new_id("plan"), goal=goal, status="init", tasks=tasks, notes=["llm planner"])


def plan_to_json(plan: Plan) -> str:
    return json.dumps(plan.to_dict(), ensure_ascii=False, indent=2)
