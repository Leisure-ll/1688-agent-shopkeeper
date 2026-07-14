from typing import Dict, List

from agent.core.state import Plan, Task, new_id
from agent.planning.schemas import PlanValidationIssue


class FallbackPlanRepairer:
    def repair(self, goal: str, memories: List[Dict[str, str]], issues: List[PlanValidationIssue]) -> Plan:
        formal_publish = any(word in goal for word in ["正式铺货", "确认铺货", "真的铺货", "执行铺货"])
        publish_tool = "request_publish_approval" if formal_publish else "publish_dry_run"
        tasks = [
            Task(new_id("task"), "检索历史经营记忆", "memory_search", {"query": goal}),
            Task(new_id("task"), "搜索候选商品", "search_products", {"query": goal, "channel": "douyin", "limit": 5}),
            Task(new_id("task"), "查询可用店铺", "list_shops", {"channel": "douyin"}),
            Task(new_id("task"), "申请正式铺货审批" if formal_publish else "铺货预检查", publish_tool, {}),
            Task(new_id("task"), "沉淀选品决策记忆", "write_memory", {"kind": "selection"}),
        ]
        return Plan(
            id=new_id("plan"),
            goal=goal,
            status="init",
            tasks=tasks,
            notes=["fallback repair planner", *[f"{issue.path}: {issue.message}" for issue in issues]],
        )
