from typing import List

from agent.core.state import Task
from agent.runtime.dag.graph import TaskGraph


class DAGScheduler:
    def order(self, tasks: List[Task]) -> List[Task]:
        return TaskGraph(tasks).topological_order()
