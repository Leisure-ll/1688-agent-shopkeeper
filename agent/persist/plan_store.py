import json
from pathlib import Path
from typing import Dict

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
