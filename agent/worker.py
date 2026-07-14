#!/usr/bin/env python3
"""Isolated worker/subagent execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Protocol

from .memory import LongTermMemory
from .state import Task, TaskStatus
from .tooling import ToolRegistry


@dataclass
class WorkerContext:
    original_goal: str
    task_goal: str
    allowed_tools: List[str]
    memory_snippets: List[str] = field(default_factory=list)


class WorkerPolicy(Protocol):
    def decide_next_action(self, task: Task, observation: Dict[str, Any], step_index: int) -> Dict[str, Any]:
        ...


class DeterministicWorkerPolicy:
    def decide_next_action(self, task: Task, observation: Dict[str, Any], step_index: int) -> Dict[str, Any]:
        if step_index > 0 and observation:
            return {"type": "done", "thought": "task has an observation; stop the worker loop"}
        return {
            "type": "tool",
            "tool_name": task.tool_name,
            "thought": (
                "Use the task-specific tool with isolated context. "
                "Do not access global conversation or tools outside the worker whitelist."
            ),
        }


class LLMWorkerPolicy:
    """Interface placeholder for LLM-driven worker decisions."""

    def __init__(self, provider):
        self.provider = provider

    def decide_next_action(self, task: Task, observation: Dict[str, Any], step_index: int) -> Dict[str, Any]:
        return self.provider.decide_worker_action(task=task.to_dict(), observation=observation, step_index=step_index)


class WorkerAgent:
    """Executes one task with a restricted context and tool whitelist.

    The worker does not receive the full conversation or whole plan by default.
    That gives the same practical context isolation as Kugelblitz subagents.
    """

    def __init__(self, tools: ToolRegistry, memory: LongTermMemory, policy: WorkerPolicy = None):
        self.tools = tools
        self.memory = memory
        self.max_steps = 4
        self.policy = policy or DeterministicWorkerPolicy()

    def execute(self, task: Task, original_goal: str, allowed_tools: List[str], scratch: Dict[str, Any]) -> Task:
        memory_items = self.memory.search(task.goal, limit=3)
        ctx = WorkerContext(
            original_goal=original_goal,
            task_goal=task.goal,
            allowed_tools=allowed_tools,
            memory_snippets=[f"{item.section}/{item.key}: {item.value}" for item in memory_items],
        )

        task.status = TaskStatus.DOING
        steps: List[Dict[str, Any]] = []
        observation: Dict[str, Any] = {}
        try:
            for step_index in range(self.max_steps):
                decision = self.policy.decide_next_action(task, observation, step_index)
                if decision["type"] == "done":
                    break

                tool_name = decision["tool_name"]
                args = self._resolve_args(task, scratch)
                result = self.tools.call(tool_name, ctx.allowed_tools, **args)
                observation = result
                steps.append(
                    {
                        "step": step_index + 1,
                        "thought": decision["thought"],
                        "tool_name": tool_name,
                        "args": args,
                        "observation_success": result.get("success", False),
                        "observation_markdown": result.get("markdown", "")[:300],
                    }
                )
                task.result = result
                if result.get("success", False):
                    break

            task.result.setdefault("data", {})
            task.result["data"]["_react_steps"] = steps
            task.status = TaskStatus.DONE if task.result.get("success", False) else TaskStatus.FAILED
            task.finished_reason = task.result.get("markdown", "")[:300]
        except Exception as exc:
            task.status = TaskStatus.FAILED
            task.result = {"success": False, "markdown": str(exc), "data": {"error": str(exc), "_react_steps": steps}}
            task.finished_reason = str(exc)
        return task

    def _resolve_args(self, task: Task, scratch: Dict[str, Any]) -> Dict[str, Any]:
        args = dict(task.args)
        if task.action == "rank_products":
            args["products"] = scratch.get("products", [])
        if task.action == "generate_advice":
            args["products"] = scratch.get("selected_products", [])
            args["shops"] = scratch.get("shops", [])
            args["publish"] = scratch.get("publish_dry_run", {})
        if task.action == "request_publish_approval":
            args["item_ids"] = [item["id"] for item in scratch.get("selected_products", [])[:5] if item.get("id")]
            shops = scratch.get("shops", [])
            authorized = [shop for shop in shops if shop.get("is_authorized")]
            args["shop_code"] = authorized[0]["code"] if len(authorized) == 1 else ""
        if task.action == "publish_dry_run":
            if not args.get("item_ids"):
                args["item_ids"] = [item["id"] for item in scratch.get("selected_products", [])[:5] if item.get("id")]
            if not args.get("shop_code"):
                shops = scratch.get("shops", [])
                authorized = [shop for shop in shops if shop.get("is_authorized")]
                args["shop_code"] = authorized[0]["code"] if len(authorized) == 1 else ""
        return args
