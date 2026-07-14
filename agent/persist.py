#!/usr/bin/env python3
"""Persistence for plans and checkpoints."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Union

from .state import Checkpoint, Plan


class AgentStore:
    def __init__(self, workspace: Union[str, Path] = ".agent_data"):
        self.root = Path(workspace)
        self.plans_dir = self.root / "plans"
        self.memory_dir = self.root / "memory"
        self.plans_dir.mkdir(parents=True, exist_ok=True)
        self.memory_dir.mkdir(parents=True, exist_ok=True)

    def plan_dir(self, plan_id: str) -> Path:
        path = self.plans_dir / plan_id
        path.mkdir(parents=True, exist_ok=True)
        (path / "checkpoints").mkdir(parents=True, exist_ok=True)
        return path

    def save_plan(self, plan: Plan, reason: str = "") -> Checkpoint:
        plan.version += 1
        checkpoint = Checkpoint(version=plan.version, reason=reason, plan=plan.to_dict())
        plan_path = self.plan_dir(plan.id) / "plan.json"
        plan_path.write_text(json.dumps(plan.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

        jsonl_path = self.plan_dir(plan.id) / "plan.jsonl"
        with jsonl_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(plan.to_dict(), ensure_ascii=False) + "\n")

        cp_path = self.plan_dir(plan.id) / "checkpoints" / f"{checkpoint.version}.json"
        cp_path.write_text(json.dumps(checkpoint.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return checkpoint

    def load_plan(self, plan_id: str) -> Plan:
        plan_path = self.plan_dir(plan_id) / "plan.json"
        return Plan.from_dict(json.loads(plan_path.read_text(encoding="utf-8")))

    def load_checkpoint(self, plan_id: str, version: int) -> Optional[Checkpoint]:
        cp_path = self.plan_dir(plan_id) / "checkpoints" / f"{version}.json"
        if not cp_path.exists():
            return None
        data = json.loads(cp_path.read_text(encoding="utf-8"))
        return Checkpoint(
            version=int(data["version"]),
            reason=data.get("reason", ""),
            plan=data["plan"],
            timestamp=float(data.get("timestamp", 0)),
        )

    def memory_path(self) -> Path:
        return self.memory_dir / "MEMORY.md"

    def graph_path(self) -> Path:
        return self.memory_dir / "memory_graph.jsonl"

    def subagent_trace_dir(self) -> Path:
        path = self.root / "subagents"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def approval_dir(self) -> Path:
        path = self.root / "approvals"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def observability_dir(self) -> Path:
        path = self.root / "observability"
        path.mkdir(parents=True, exist_ok=True)
        return path
