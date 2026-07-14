from typing import Any, Dict, List, Protocol


class JSONPlannerProvider(Protocol):
    def create_plan(self, goal: str, memories: List[Dict[str, str]]) -> Dict[str, Any]:
        ...

    def repair_plan(
        self,
        goal: str,
        memories: List[Dict[str, str]],
        invalid_plan: Dict[str, Any],
        issues: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        ...
