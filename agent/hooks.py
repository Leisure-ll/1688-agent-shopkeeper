#!/usr/bin/env python3
"""Runtime event hooks, modeled after Kugelblitz AgentEventHooks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional


@dataclass
class AgentEventHooks:
    on_run_start: Optional[Callable[[str, str], None]] = None
    on_run_end: Optional[Callable[[str, bool], None]] = None
    on_state_transition: Optional[Callable[[str, str], None]] = None
    on_plan_created: Optional[Callable[[str, int], None]] = None
    on_subagent_spawned: Optional[Callable[[str, str, str, bool], None]] = None
    on_task_updated: Optional[Callable[[str, str, str], None]] = None
    on_tool_call_end: Optional[Callable[[str, Dict[str, Any]], None]] = None
    on_approval_created: Optional[Callable[[str, str], None]] = None
    on_error: Optional[Callable[[str, Exception], None]] = None


def chain(original: AgentEventHooks, system: AgentEventHooks) -> AgentEventHooks:
    """Return hooks where system callbacks run before original callbacks."""

    result = AgentEventHooks(**original.__dict__)
    for field in result.__dataclass_fields__:
        sys_cb = getattr(system, field)
        prev_cb = getattr(result, field)
        if sys_cb is None:
            continue

        def chained(*args, _sys=sys_cb, _prev=prev_cb):
            _sys(*args)
            if _prev is not None:
                _prev(*args)

        setattr(result, field, chained)
    return result
