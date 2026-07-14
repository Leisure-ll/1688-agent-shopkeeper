from agent.core.state import Plan
from agent.planning.reviewer import FailureReviewer


class PlanAdaptor:
    def __init__(self):
        self.reviewer = FailureReviewer()

    def adapt(self, plan: Plan, error: str) -> bool:
        changed = False
        for task in plan.tasks:
            if task.status == "failed":
                report = self.reviewer.review(plan, task, error)
                plan.notes.append(f"reviewer: {report.action} / {report.reason}")
                if not report.recoverable:
                    return False
                if report.action == "broaden_search":
                    query = str(task.args.get("query", plan.goal))
                    task.args["query"] = query.replace("适合抖店卖的", "").strip() or plan.goal
                    task.args["limit"] = max(int(task.args.get("limit", 5)), 10)
                task.status = "pending"
                task.error = None
                changed = True
        if changed:
            plan.notes.append(f"adapted failed tasks after error: {error}")
        return changed
