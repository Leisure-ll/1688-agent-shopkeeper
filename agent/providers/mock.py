from typing import Any, Dict, List


class MockJSONPlannerProvider:
    def __init__(self, payload: Dict[str, Any]):
        self.payload = payload

    def create_plan(self, goal: str, memories: List[Dict[str, str]]) -> Dict[str, Any]:
        return self.payload

    def repair_plan(self, goal: str, memories: List[Dict[str, str]], invalid_plan: Dict[str, Any], issues: List[Dict[str, str]]) -> Dict[str, Any]:
        return self.payload
