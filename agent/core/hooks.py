from typing import Any, Callable, Iterable


class AgentEventHooks:
    def on_state_transition(self, **event: Any) -> None:
        pass

    def on_plan_created(self, **event: Any) -> None:
        pass

    def on_checkpoint(self, **event: Any) -> None:
        pass

    def on_subagent_spawned(self, **event: Any) -> None:
        pass

    def on_tool_start(self, **event: Any) -> None:
        pass

    def on_tool_end(self, **event: Any) -> None:
        pass

    def on_task_updated(self, **event: Any) -> None:
        pass

    def on_goal_drift(self, **event: Any) -> None:
        pass


class _ChainedHooks(AgentEventHooks):
    def __init__(self, hooks: Iterable[AgentEventHooks]):
        self._hooks = list(hooks)

    def _call(self, name: str, event: dict) -> None:
        for hook in self._hooks:
            method: Callable[..., None] = getattr(hook, name)
            method(**event)

    def on_state_transition(self, **event: Any) -> None:
        self._call("on_state_transition", event)

    def on_plan_created(self, **event: Any) -> None:
        self._call("on_plan_created", event)

    def on_checkpoint(self, **event: Any) -> None:
        self._call("on_checkpoint", event)

    def on_subagent_spawned(self, **event: Any) -> None:
        self._call("on_subagent_spawned", event)

    def on_tool_start(self, **event: Any) -> None:
        self._call("on_tool_start", event)

    def on_tool_end(self, **event: Any) -> None:
        self._call("on_tool_end", event)

    def on_task_updated(self, **event: Any) -> None:
        self._call("on_task_updated", event)

    def on_goal_drift(self, **event: Any) -> None:
        self._call("on_goal_drift", event)


def chain(*hooks: AgentEventHooks) -> AgentEventHooks:
    return _ChainedHooks([hook for hook in hooks if hook])
