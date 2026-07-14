from typing import Callable, Dict

from agent.core.state import Plan, Task
from agent.runtime.dag.graph import TaskGraph


TaskRunner = Callable[[Task, Dict[str, object]], Dict[str, object]]
TaskCallback = Callable[[Task], None]


class DAGPlanExecutor:
    def __init__(self, runner: TaskRunner, on_task_update: TaskCallback):
        self.runner = runner
        self.on_task_update = on_task_update

    def run(self, plan: Plan, context: Dict[str, object]) -> None:
        graph = TaskGraph(plan.tasks)
        completed = set()
        for task in graph.topological_order():
            missing = [dep for dep in task.depends_on if dep not in completed]
            if missing:
                task.status = "blocked"
                task.error = f"blocked by incomplete dependencies: {missing}"
                self.on_task_update(task)
                continue
            task.status = "running"
            self.on_task_update(task)
            try:
                result = self.runner(task, context)
                task.result = result
                task.status = "done"
                completed.add(task.id)
                self.on_task_update(task)
            except Exception as exc:
                task.error = str(exc)
                task.status = "failed"
                self.on_task_update(task)
                for child_id in graph.downstream_of(task.id):
                    child = graph.by_id[child_id]
                    if child.status == "pending":
                        child.status = "blocked"
                        child.error = f"blocked by failed dependency: {task.id}"
                        self.on_task_update(child)
                raise
