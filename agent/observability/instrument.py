from typing import Any, Dict

from agent.core.hooks import AgentEventHooks
from agent.observability.observer import Observer


class HookInstrument(AgentEventHooks):
    def __init__(self, observer: Observer):
        self.observer = observer

    def _event(self, name: str, event: Dict[str, Any]) -> None:
        span = self.observer.start_span(name, event)
        self.observer.end_span(span, event.get("error"))

    def on_state_transition(self, **event: Any) -> None:
        self._event("state.transition", event)

    def on_plan_created(self, **event: Any) -> None:
        self._event("planner.create_plan", event)

    def on_checkpoint(self, **event: Any) -> None:
        self._event("plan.checkpoint", event)

    def on_subagent_spawned(self, **event: Any) -> None:
        self._event("subagent.spawn", event)

    def on_tool_start(self, **event: Any) -> None:
        self._event(f"tool:{event.get('tool')}:start", event)

    def on_tool_end(self, **event: Any) -> None:
        self._event(f"tool:{event.get('tool')}:end", event)

    def on_task_updated(self, **event: Any) -> None:
        self._event("task.updated", event)

    def on_goal_drift(self, **event: Any) -> None:
        self._event("goal.drift", event)
