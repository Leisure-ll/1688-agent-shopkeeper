import json
from typing import Any, Dict, List, Protocol

from agent.core.state import Plan, Task, new_id
from agent.planning.repair import FallbackPlanRepairer
from agent.planning.schemas import PlanValidationIssue
from agent.planning.validator import build_plan_from_payload, validate_plan_payload


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
        self.repairer = FallbackPlanRepairer()

    def create_plan(self, goal: str, memories: List[Dict[str, str]] = None) -> Plan:
        memories = memories or []
        data = self.provider.create_plan(goal, memories or [])
        issues = validate_plan_payload(data)
        if not issues:
            return build_plan_from_payload(data, goal, "llm planner")

        repaired = self._repair_with_provider(goal, memories, data, issues)
        if repaired:
            repaired_issues = validate_plan_payload(repaired)
            if not repaired_issues:
                plan = build_plan_from_payload(repaired, goal, "llm planner repaired")
                plan.notes.extend(f"original issue: {issue.path}: {issue.message}" for issue in issues)
                return plan
            issues = repaired_issues

        return self.repairer.repair(goal, memories, issues)

    def _repair_with_provider(
        self,
        goal: str,
        memories: List[Dict[str, str]],
        data: Dict[str, Any],
        issues: List[PlanValidationIssue],
    ) -> Dict[str, Any]:
        repair_plan = getattr(self.provider, "repair_plan", None)
        if not repair_plan:
            return {}
        return repair_plan(goal, memories, data, [issue.to_dict() for issue in issues])


def plan_to_json(plan: Plan) -> str:
    return json.dumps(plan.to_dict(), ensure_ascii=False, indent=2)
