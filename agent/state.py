#!/usr/bin/env python3
"""Shared state types for the 1688 shopkeeper agent."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional, Set
import time
import uuid


class PlanState(str, Enum):
    INTENT = "intent"
    DIRECT = "direct"
    INIT = "init"
    CONFIRMED = "confirmed"
    DOING = "doing"
    UPDATING = "updating"
    DONE = "done"
    FAILED = "failed"
    REJECTED = "rejected"


class TaskStatus(str, Enum):
    PENDING = "pending"
    DOING = "doing"
    DONE = "done"
    FAILED = "failed"


@dataclass
class Task:
    goal: str
    action: str
    tool_name: str = ""
    args: Dict[str, Any] = field(default_factory=dict)
    parent_task_ids: List[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: f"task_{uuid.uuid4().hex[:8]}")
    status: TaskStatus = TaskStatus.PENDING
    result: Dict[str, Any] = field(default_factory=dict)
    finished_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        task = cls(
            goal=data["goal"],
            action=data["action"],
            tool_name=data.get("tool_name", ""),
            args=data.get("args", {}) or {},
            parent_task_ids=data.get("parent_task_ids", []) or [],
            id=data.get("id") or f"task_{uuid.uuid4().hex[:8]}",
        )
        task.status = TaskStatus(data.get("status", TaskStatus.PENDING.value))
        task.result = data.get("result", {}) or {}
        task.finished_reason = data.get("finished_reason", "")
        return task


@dataclass
class Plan:
    name: str
    original_goal: str
    tasks: List[Task]
    id: str = field(default_factory=lambda: f"plan_{uuid.uuid4().hex[:10]}")
    state: PlanState = PlanState.INIT
    version: int = 0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    finished_reason: str = ""

    def validate(self) -> None:
        if not self.tasks:
            raise ValueError("plan must contain at least one task")

        task_ids = {task.id for task in self.tasks}
        for task in self.tasks:
            for parent_id in task.parent_task_ids:
                if parent_id not in task_ids:
                    raise ValueError(f"task {task.id} depends on missing task {parent_id}")
                if parent_id == task.id:
                    raise ValueError(f"task {task.id} depends on itself")

        visiting: Set[str] = set()
        visited: Set[str] = set()
        parents = {task.id: task.parent_task_ids for task in self.tasks}

        def visit(task_id: str) -> None:
            if task_id in visiting:
                raise ValueError(f"plan contains dependency cycle at {task_id}")
            if task_id in visited:
                return
            visiting.add(task_id)
            for parent_id in parents.get(task_id, []):
                visit(parent_id)
            visiting.remove(task_id)
            visited.add(task_id)

        for task_id in task_ids:
            visit(task_id)

    def ready_tasks(self) -> List[Task]:
        status_by_id = {task.id: task.status for task in self.tasks}
        ready: List[Task] = []
        for task in self.tasks:
            if task.status != TaskStatus.PENDING:
                continue
            if all(status_by_id.get(parent_id) == TaskStatus.DONE for parent_id in task.parent_task_ids):
                ready.append(task)
        return ready

    def is_complete(self) -> bool:
        return all(task.status == TaskStatus.DONE for task in self.tasks)

    def has_failure(self) -> bool:
        return any(task.status == TaskStatus.FAILED for task in self.tasks)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "original_goal": self.original_goal,
            "tasks": [task.to_dict() for task in self.tasks],
            "state": self.state.value,
            "version": self.version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "finished_reason": self.finished_reason,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Plan":
        plan = cls(
            id=data["id"],
            name=data["name"],
            original_goal=data.get("original_goal", ""),
            tasks=[Task.from_dict(item) for item in data.get("tasks", [])],
            created_at=data.get("created_at", time.time()),
        )
        plan.state = PlanState(data.get("state", PlanState.INIT.value))
        plan.version = int(data.get("version", 0))
        plan.updated_at = data.get("updated_at", time.time())
        plan.finished_reason = data.get("finished_reason", "")
        return plan


@dataclass
class Checkpoint:
    version: int
    reason: str
    plan: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AgentRunResult:
    success: bool
    state: PlanState
    markdown: str
    data: Dict[str, Any] = field(default_factory=dict)
    plan: Optional[Plan] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "state": self.state.value,
            "markdown": self.markdown,
            "data": self.data,
            "plan": self.plan.to_dict() if self.plan else None,
        }
