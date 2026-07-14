#!/usr/bin/env python3
"""Dynamic subagent spawning for task execution."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
import time
import uuid
from typing import Any, Dict, List

from .memory import LongTermMemory
from .state import Task
from .tooling import ToolRegistry, worker_tools
from .worker import WorkerAgent


@dataclass
class SubAgentTrace:
    id: str
    task_id: str
    task_goal: str
    original_goal: str
    allowed_tools: List[str]
    memory_snippets: List[str]
    started_at: float = field(default_factory=time.time)
    finished_at: float = 0.0
    status: str = "running"
    result: Dict[str, Any] = field(default_factory=dict)
    steps: List[Dict[str, Any]] = field(default_factory=list)


class SubAgentManager:
    """Creates short-lived subagents at execution time.

    The planner never directly executes tools. During `doing`, the runtime
    dynamically spawns a subagent for each ready task. The spawned agent gets a
    minimal context and its own execution-tool whitelist.
    """

    def __init__(self, tools: ToolRegistry, memory: LongTermMemory, trace_dir: str | Path):
        self.tools = tools
        self.memory = memory
        self.trace_dir = Path(trace_dir)
        self.trace_dir.mkdir(parents=True, exist_ok=True)

    def spawn(self, task: Task, original_goal: str, scratch: Dict[str, Any]) -> Task:
        memory_items = self.memory.search(task.goal, limit=3)
        trace = SubAgentTrace(
            id=f"subagent_{uuid.uuid4().hex[:10]}",
            task_id=task.id,
            task_goal=task.goal,
            original_goal=original_goal,
            allowed_tools=worker_tools(),
            memory_snippets=[f"{item.section}/{item.key}: {item.value}" for item in memory_items],
        )
        self._write_trace(trace)

        worker = WorkerAgent(self.tools, self.memory)
        updated = worker.execute(task, original_goal, trace.allowed_tools, scratch)

        trace.finished_at = time.time()
        trace.status = updated.status.value
        trace.result = updated.result
        trace.steps = (updated.result.get("data", {}) or {}).get("_react_steps", [])
        self._write_trace(trace)
        return updated

    def _write_trace(self, trace: SubAgentTrace) -> None:
        path = self.trace_dir / f"{trace.id}.json"
        path.write_text(json.dumps(asdict(trace), ensure_ascii=False, indent=2), encoding="utf-8")
