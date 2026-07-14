from dataclasses import dataclass

from agent.core.state import Plan, Task


@dataclass
class ReviewReport:
    recoverable: bool
    action: str
    reason: str


class FailureReviewer:
    def review(self, plan: Plan, task: Task, error: str) -> ReviewReport:
        if "not allowed" in error:
            return ReviewReport(False, "deny", "policy violation cannot be auto-replanned")
        if "cycle detected" in error or "unknown task" in error:
            return ReviewReport(False, "deny", "invalid DAG cannot be auto-replanned")
        if task.tool == "search_products":
            return ReviewReport(True, "broaden_search", "product search failed; broaden query and retry")
        if task.tool in {"list_shops", "publish_dry_run", "memory_search", "write_memory"}:
            return ReviewReport(True, "retry", f"{task.tool} failed; retry once after checkpoint")
        return ReviewReport(False, "deny", f"no recovery rule for tool {task.tool}")
