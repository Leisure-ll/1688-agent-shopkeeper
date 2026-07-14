#!/usr/bin/env python3
"""Tool registry and state tool whitelist."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List

from .state import PlanState


ToolFn = Callable[..., Dict[str, Any]]


@dataclass
class ToolSpec:
    name: str
    description: str
    fn: ToolFn
    risk: str = "read"


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        self._tools[spec.name] = spec

    def get(self, name: str) -> ToolSpec:
        if name not in self._tools:
            raise KeyError(f"unknown tool: {name}")
        return self._tools[name]

    def names(self) -> List[str]:
        return sorted(self._tools)

    def call(self, name: str, allowed: Iterable[str], **kwargs: Any) -> Dict[str, Any]:
        allowed_set = set(allowed)
        if name not in allowed_set:
            raise PermissionError(f"tool {name!r} is not allowed in current state")
        spec = self.get(name)
        return spec.fn(**kwargs)


STATE_TOOL_WHITELIST: Dict[PlanState, List[str]] = {
    PlanState.INTENT: ["set_work_mode"],
    PlanState.DIRECT: [
        "memory_search",
        "memory_store",
        "search_products",
        "product_detail",
        "list_shops",
        "fetch_trend",
        "fetch_opportunities",
        "shop_daily",
    ],
    PlanState.INIT: [
        "plan_create",
        "task_insert",
        "memory_search",
        "memory_store",
    ],
    PlanState.CONFIRMED: ["ask_human", "confirm_plan"],
    PlanState.DOING: ["task_query", "task_status_update", "worker_spawn"],
    PlanState.UPDATING: [
        "task_query",
        "task_status_update",
        "task_insert",
        "plan_query",
        "memory_search",
        "memory_store",
    ],
    PlanState.DONE: ["task_query", "plan_query", "memory_store"],
    PlanState.FAILED: ["task_query", "plan_query", "memory_store"],
    PlanState.REJECTED: [],
}


def tools_for_state(state: PlanState) -> List[str]:
    return STATE_TOOL_WHITELIST.get(state, [])


WORKER_TOOL_WHITELIST: List[str] = [
    "memory_search",
    "search_products",
    "rank_products",
    "product_detail",
    "list_shops",
    "fetch_trend",
    "fetch_opportunities",
    "shop_daily",
    "publish_dry_run",
    "request_publish_approval",
    "generate_advice",
]


def worker_tools() -> List[str]:
    return list(WORKER_TOOL_WHITELIST)
