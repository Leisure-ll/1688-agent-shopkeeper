from collections import defaultdict
from typing import Dict, List, Set

from agent.core.state import Task


class DAGValidationError(ValueError):
    pass


class TaskGraph:
    def __init__(self, tasks: List[Task]):
        self.tasks = tasks
        self.by_id: Dict[str, Task] = {task.id: task for task in tasks}
        if len(self.by_id) != len(tasks):
            raise DAGValidationError("duplicate task ids are not allowed")
        self.children: Dict[str, List[str]] = defaultdict(list)
        self.indegree: Dict[str, int] = {task.id: 0 for task in tasks}
        for task in tasks:
            for dep in task.depends_on:
                if dep not in self.by_id:
                    raise DAGValidationError(f"task {task.id} depends on unknown task {dep}")
                self.children[dep].append(task.id)
                self.indegree[task.id] += 1

    def topological_order(self) -> List[Task]:
        indegree = dict(self.indegree)
        ready = [task_id for task_id, degree in indegree.items() if degree == 0]
        order: List[Task] = []
        while ready:
            task_id = ready.pop(0)
            order.append(self.by_id[task_id])
            for child in self.children.get(task_id, []):
                indegree[child] -= 1
                if indegree[child] == 0:
                    ready.append(child)
        if len(order) != len(self.tasks):
            unresolved = sorted(set(self.by_id) - {task.id for task in order})
            raise DAGValidationError(f"cycle detected in task graph: {unresolved}")
        return order

    def downstream_of(self, task_id: str) -> Set[str]:
        seen: Set[str] = set()
        queue = list(self.children.get(task_id, []))
        while queue:
            current = queue.pop(0)
            if current in seen:
                continue
            seen.add(current)
            queue.extend(self.children.get(current, []))
        return seen
