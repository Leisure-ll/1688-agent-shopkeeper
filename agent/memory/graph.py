from typing import Dict


def product_selection_event(plan_id: str, product_id: str, reason: str) -> Dict[str, str]:
    return {
        "type": "selected_product",
        "plan_id": plan_id,
        "product_id": product_id,
        "reason": reason,
    }
