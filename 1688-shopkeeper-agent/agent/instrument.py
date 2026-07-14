#!/usr/bin/env python3
"""Hook-driven observability instrument."""

from __future__ import annotations

from typing import Dict

from .hooks import AgentEventHooks
from .observability import Observer, Span


class HookInstrument:
    """Converts runtime hooks into observer traces and spans."""

    def __init__(self, observer: Observer):
        self.observer = observer
        self.trace: Span | None = None

    def hooks(self) -> AgentEventHooks:
        return AgentEventHooks(
            on_run_start=self.on_run_start,
            on_run_end=self.on_run_end,
            on_state_transition=self.on_state_transition,
            on_plan_created=self.on_plan_created,
            on_subagent_spawned=self.on_subagent_spawned,
            on_task_updated=self.on_task_updated,
            on_tool_call_end=self.on_tool_call_end,
            on_approval_created=self.on_approval_created,
            on_error=self.on_error,
        )

    def on_run_start(self, name: str, goal: str) -> None:
        self.trace = self.observer.start_trace(name, goal)

    def on_run_end(self, state: str, success: bool) -> None:
        if self.trace:
            self.trace.set_attributes({"state": state, "success": success})
            self.trace.end()
            self.trace = None
        flush = getattr(self.observer, "flush", None)
        if callable(flush):
            flush()

    def on_state_transition(self, old: str, new: str) -> None:
        if self.trace:
            span = self.trace.start_span("state.transition", {"from": old, "to": new})
            span.end()

    def on_plan_created(self, plan_id: str, task_count: int) -> None:
        if self.trace:
            span = self.trace.start_span("planner.create_plan", {"plan_id": plan_id, "task_count": task_count})
            span.end()

    def on_subagent_spawned(self, task_id: str, tool_name: str, status: str, success: bool) -> None:
        if self.trace:
            span = self.trace.start_span(
                "subagent.spawn",
                {"task_id": task_id, "tool": tool_name, "status": status, "success": success},
            )
            span.end()

    def on_task_updated(self, task_id: str, status: str, output: str) -> None:
        if self.trace:
            span = self.trace.start_span("task.updated", {"task_id": task_id, "status": status, "output": output[:300]})
            span.end()

    def on_tool_call_end(self, tool_name: str, result: Dict) -> None:
        if self.trace:
            span = self.trace.start_span("tool:" + tool_name, {"output": result})
            span.end()

    def on_approval_created(self, approval_id: str, action: str) -> None:
        if self.trace:
            span = self.trace.start_span("approval.created", {"approval_id": approval_id, "action": action})
            span.end()

    def on_error(self, where: str, err: Exception) -> None:
        if self.trace:
            span = self.trace.start_span("error", {"where": where})
            span.record_error(err)
            span.end()
