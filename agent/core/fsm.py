from datetime import datetime
from typing import Dict

from agent.core.hooks import AgentEventHooks
from agent.core.state import Plan
from agent.persist.plan_store import PlanStore
from agent.planning.goal_drift import detect_goal_drift
from agent.runtime.worker import AgentWorker


class PlanModeFSM:
    STATES = {"intent", "init", "confirmed", "doing", "updating", "done", "failed", "rejected"}

    def __init__(self, store: PlanStore, worker: AgentWorker, hooks: AgentEventHooks):
        self.store = store
        self.worker = worker
        self.hooks = hooks

    def transition(self, plan: Plan, to_state: str, reason: str) -> None:
        if to_state not in self.STATES:
            raise ValueError(f"unknown state: {to_state}")
        old = plan.status
        plan.status = to_state
        plan.updated_at = datetime.utcnow().isoformat() + "Z"
        self.hooks.on_state_transition(plan_id=plan.id, old=old, new=to_state, reason=reason)
        checkpoint = self.store.checkpoint(plan, reason)
        self.hooks.on_checkpoint(plan_id=plan.id, path=str(checkpoint), reason=reason)

    def detect_goal_drift(self, plan: Plan, task_result: Dict[str, object]) -> bool:
        reason = detect_goal_drift(plan.goal, task_result)
        if reason:
            plan.drift_count += 1
            self.hooks.on_goal_drift(plan_id=plan.id, reason=reason, drift_count=plan.drift_count)
            return True
        return False

    def run(self, plan: Plan, auto_confirm: bool = False) -> Plan:
        self.store.save(plan)
        self.hooks.on_plan_created(plan_id=plan.id, goal=plan.goal, task_count=len(plan.tasks))
        if auto_confirm:
            self.transition(plan, "confirmed", "auto confirmed")
        if plan.status in {"init", "intent"}:
            return plan
        self.transition(plan, "doing", "start execution")
        context: Dict[str, object] = {}
        for task in plan.tasks:
            try:
                task.status = "running"
                self.hooks.on_task_updated(plan_id=plan.id, task_id=task.id, status=task.status)
                result = self.worker.run(task, context)
                task.result = result
                task.status = "done"
                self.detect_goal_drift(plan, result)
            except Exception as exc:
                task.error = str(exc)
                task.status = "failed"
                self.transition(plan, "failed", str(exc))
                return plan
            self.hooks.on_task_updated(plan_id=plan.id, task_id=task.id, status=task.status)
            self.store.checkpoint(plan, f"task {task.id} {task.status}")
        self.transition(plan, "done", "all tasks completed")
        return plan
