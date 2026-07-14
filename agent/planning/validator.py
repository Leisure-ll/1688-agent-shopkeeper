from typing import Any, Dict, List, Set

from agent.core.state import Plan, Task, new_id
from agent.planning.schemas import ALLOWED_PLANNER_TOOLS, FORBIDDEN_PLANNER_TOOLS, PlanValidationIssue


def validate_plan_payload(payload: Dict[str, Any]) -> List[PlanValidationIssue]:
    issues: List[PlanValidationIssue] = []
    if not isinstance(payload, dict):
        return [PlanValidationIssue("$", "planner output must be a JSON object")]
    tasks = payload.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        return [PlanValidationIssue("$.tasks", "tasks must be a non-empty array")]

    seen: Set[str] = set()
    for idx, task in enumerate(tasks):
        path = f"$.tasks[{idx}]"
        if not isinstance(task, dict):
            issues.append(PlanValidationIssue(path, "task must be an object"))
            continue
        title = task.get("title")
        if not isinstance(title, str) or not title.strip():
            issues.append(PlanValidationIssue(f"{path}.title", "title must be a non-empty string"))
        tool = task.get("tool")
        if tool in FORBIDDEN_PLANNER_TOOLS:
            issues.append(PlanValidationIssue(f"{path}.tool", f"{tool} is forbidden; use approval flow"))
        elif tool not in ALLOWED_PLANNER_TOOLS:
            issues.append(PlanValidationIssue(f"{path}.tool", f"tool must be one of {sorted(ALLOWED_PLANNER_TOOLS)}"))
        args = task.get("args", {})
        if not isinstance(args, dict):
            issues.append(PlanValidationIssue(f"{path}.args", "args must be an object"))
        depends_on = task.get("depends_on", [])
        if not isinstance(depends_on, list) or not all(isinstance(item, str) for item in depends_on):
            issues.append(PlanValidationIssue(f"{path}.depends_on", "depends_on must be an array of strings"))
        task_id = task.get("id")
        if task_id is not None:
            if not isinstance(task_id, str) or not task_id.strip():
                issues.append(PlanValidationIssue(f"{path}.id", "id must be a non-empty string when provided"))
            elif task_id in seen:
                issues.append(PlanValidationIssue(f"{path}.id", f"duplicate task id {task_id}"))
            else:
                seen.add(task_id)

    known_ids = {task.get("id") for task in tasks if isinstance(task, dict) and isinstance(task.get("id"), str)}
    for idx, task in enumerate(tasks):
        if not isinstance(task, dict):
            continue
        for dep in task.get("depends_on", []) or []:
            if known_ids and dep not in known_ids:
                issues.append(PlanValidationIssue(f"$.tasks[{idx}].depends_on", f"unknown dependency {dep}"))
    return issues


def build_plan_from_payload(payload: Dict[str, Any], goal: str, note: str) -> Plan:
    tasks = [
        Task(
            id=item.get("id") or new_id("task"),
            title=item["title"].strip(),
            tool=item["tool"],
            args=item.get("args", {}),
            depends_on=item.get("depends_on", []),
        )
        for item in payload["tasks"]
    ]
    return Plan(id=payload.get("id") or new_id("plan"), goal=goal, status="intent", tasks=tasks, notes=[note, "schema validated"])
