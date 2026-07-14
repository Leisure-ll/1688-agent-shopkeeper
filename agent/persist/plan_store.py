import json
from pathlib import Path
from typing import Dict, List

from agent.core.state import Plan


class PlanStore:
    def __init__(self, workspace: str = ".agent_data"):
        self.root = Path(workspace)
        self.plan_root = self.root / "plans"
        self.plan_root.mkdir(parents=True, exist_ok=True)

    def plan_dir(self, plan_id: str) -> Path:
        path = self.plan_root / plan_id
        path.mkdir(parents=True, exist_ok=True)
        (path / "checkpoints").mkdir(exist_ok=True)
        return path

    def save(self, plan: Plan) -> None:
        path = self.plan_dir(plan.id) / "plan.json"
        path.write_text(json.dumps(plan.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    def checkpoint(self, plan: Plan, reason: str) -> Path:
        plan.version += 1
        self.save(plan)
        path = self.plan_dir(plan.id) / "checkpoints" / f"{plan.version}.json"
        payload: Dict[str, object] = {"reason": reason, "plan": plan.to_dict()}
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        with (self.plan_dir(plan.id) / "plan.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
        return path

    def load(self, plan_id: str) -> Plan:
        data = json.loads((self.plan_dir(plan_id) / "plan.json").read_text(encoding="utf-8"))
        return Plan.from_dict(data)

    def list_checkpoints(self, plan_id: str) -> List[Dict[str, object]]:
        checkpoint_dir = self.plan_dir(plan_id) / "checkpoints"
        rows: List[Dict[str, object]] = []
        for path in sorted(checkpoint_dir.glob("*.json"), key=lambda item: int(item.stem)):
            payload = json.loads(path.read_text(encoding="utf-8"))
            rows.append({"version": int(path.stem), "reason": payload.get("reason", ""), "path": str(path)})
        return rows

    def load_checkpoint(self, plan_id: str, version: int) -> Plan:
        path = self.plan_dir(plan_id) / "checkpoints" / f"{version}.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        return Plan.from_dict(payload["plan"])

    def replay(self, plan_id: str) -> List[Dict[str, object]]:
        path = self.plan_dir(plan_id) / "plan.jsonl"
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def diff_checkpoints(self, plan_id: str, left: int, right: int) -> Dict[str, object]:
        a = self.load_checkpoint(plan_id, left).to_dict()
        b = self.load_checkpoint(plan_id, right).to_dict()
        return {
            "plan_id": plan_id,
            "left": left,
            "right": right,
            "status": {"left": a["status"], "right": b["status"]},
            "version": {"left": a["version"], "right": b["version"]},
            "tasks": _diff_tasks(a["tasks"], b["tasks"]),
        }


def _diff_tasks(left_tasks: List[Dict[str, object]], right_tasks: List[Dict[str, object]]) -> List[Dict[str, object]]:
    left = {task["id"]: task for task in left_tasks}
    right = {task["id"]: task for task in right_tasks}
    rows: List[Dict[str, object]] = []
    for task_id in sorted(set(left) | set(right)):
        a = left.get(task_id)
        b = right.get(task_id)
        if a is None:
            rows.append({"task_id": task_id, "change": "added", "right_status": b.get("status")})
        elif b is None:
            rows.append({"task_id": task_id, "change": "removed", "left_status": a.get("status")})
        elif a.get("status") != b.get("status") or a.get("error") != b.get("error"):
            rows.append(
                {
                    "task_id": task_id,
                    "change": "updated",
                    "left_status": a.get("status"),
                    "right_status": b.get("status"),
                    "left_error": a.get("error"),
                    "right_error": b.get("error"),
                }
            )
    return rows
