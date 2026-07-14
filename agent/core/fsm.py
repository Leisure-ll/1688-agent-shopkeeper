from datetime import datetime
from typing import Dict

from agent.core.hooks import AgentEventHooks
from agent.core.state import Plan, Task
from agent.persist.plan_store import PlanStore
from agent.planning.adaptor import PlanAdaptor
from agent.planning.goal_drift import detect_goal_drift
from agent.runtime.dag.executor import DAGPlanExecutor
from agent.runtime.dag.graph import DAGValidationError
from agent.runtime.worker import AgentWorker
from agent.tools.policy import allowed_for_state


class PlanModeFSM:
    STATES = {"intent", "init", "confirmed", "doing", "updating", "done", "failed", "rejected"}

    def __init__(self, store: PlanStore, worker: AgentWorker, hooks: AgentEventHooks):
        self.store = store
        self.worker = worker
        self.hooks = hooks
        self.adaptor = PlanAdaptor()

    def transition(self, plan: Plan, to_state: str, reason: str) -> None:
        if to_state not in self.STATES:
            raise ValueError(f"unknown state: {to_state}")
        old = plan.status
        plan.status = to_state
        plan.updated_at = datetime.utcnow().isoformat() + "Z"
        self.hooks.on_state_transition(plan_id=plan.id, session_id=plan.session_id, old=old, new=to_state, reason=reason)
        checkpoint = self.store.checkpoint(plan, reason)
        self.hooks.on_checkpoint(plan_id=plan.id, session_id=plan.session_id, path=str(checkpoint), reason=reason)

    def detect_goal_drift(self, plan: Plan, task_result: Dict[str, object]) -> bool:
        reason = detect_goal_drift(plan.goal, task_result)
        if reason:
            plan.drift_count += 1
            self.hooks.on_goal_drift(plan_id=plan.id, session_id=plan.session_id, reason=reason, drift_count=plan.drift_count)
            return True
        return False

    def run(self, plan: Plan, auto_confirm: bool = False) -> Plan:
        self.store.save(plan)
        self.worker.session_id = plan.session_id
        self.hooks.on_plan_created(plan_id=plan.id, session_id=plan.session_id, goal=plan.goal, task_count=len(plan.tasks))
        if plan.status == "intent":
            self._classify_intent(plan)
        if plan.status == "failed":
            return plan
        if auto_confirm:
            self.transition(plan, "confirmed", "auto confirmed")
        if plan.status in {"init", "intent"}:
            return plan
        self.transition(plan, "doing", "start execution")
        context: Dict[str, object] = {}
        executor = DAGPlanExecutor(
            runner=lambda task, ctx: self._run_task(plan, task, ctx),
            on_task_update=lambda task: self._on_task_update(plan, task),
        )
        try:
            executor.run(plan, context)
        except (DAGValidationError, Exception) as exc:
            self.transition(plan, "updating", str(exc))
            if not self.adaptor.adapt(plan, str(exc)):
                self.transition(plan, "failed", "adaptation unavailable")
                return plan
            if not auto_confirm:
                return plan
            self.transition(plan, "confirmed", "adapted plan auto confirmed")
            self.transition(plan, "doing", "resume adapted plan")
            try:
                executor.run(plan, context)
            except Exception as retry_exc:
                self.transition(plan, "failed", str(retry_exc))
                return plan
            self.transition(plan, "done", "adapted plan completed")
            return plan
        self.transition(plan, "done", "all tasks completed")
        return plan

    def _run_task(self, plan: Plan, task, context: Dict[str, object]) -> Dict[str, object]:
        if task.tool not in allowed_for_state(plan.status):
            raise PermissionError(f"tool {task.tool} is not allowed in state {plan.status}")
        result = self.worker.run(task, context)
        self.detect_goal_drift(plan, result)
        return result

    def _classify_intent(self, plan: Plan) -> None:
        task = Task("intent_classifier", "判断目标复杂度", "classify_intent", {"goal": plan.goal})
        context: Dict[str, object] = {}
        try:
            task.status = "running"
            self.hooks.on_task_updated(plan_id=plan.id, task_id=task.id, status=task.status)
            result = self._run_task(plan, task, context)
            task.result = result
            task.status = "done"
            plan.notes.append(f"intent: {result.get('complexity')} / {result.get('route')}")
            self._on_task_update(plan, task)
            self.transition(plan, "init", "intent classified")
        except Exception as exc:
            task.error = str(exc)
            task.status = "failed"
            self._on_task_update(plan, task)
            self.transition(plan, "failed", str(exc))

    def _on_task_update(self, plan: Plan, task) -> None:
        self.hooks.on_task_updated(plan_id=plan.id, session_id=plan.session_id, task_id=task.id, status=task.status)
        if task.status in {"done", "failed", "blocked"}:
            self.store.checkpoint(plan, f"task {task.id} {task.status}")
