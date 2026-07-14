from agent.core.state import Plan


class PlanAdaptor:
    def adapt(self, plan: Plan, error: str) -> bool:
        if "not allowed" in error or "cycle detected" in error or "unknown task" in error:
            plan.notes.append(f"adaptation skipped: {error}")
            return False
        changed = False
        for task in plan.tasks:
            if task.status == "failed":
                task.status = "pending"
                task.error = None
                changed = True
        if changed:
            plan.notes.append(f"adapted failed tasks after error: {error}")
        return changed
