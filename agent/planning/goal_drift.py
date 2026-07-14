from typing import Dict


def detect_goal_drift(goal: str, task_result: Dict[str, object]) -> str:
    if task_result.get("error"):
        return str(task_result["error"])
    products = task_result.get("products")
    if isinstance(products, list) and "连衣裙" in goal and not products:
        return "goal expected dress products but search returned empty"
    return ""
