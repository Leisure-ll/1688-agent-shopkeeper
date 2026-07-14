from dataclasses import dataclass
from typing import Dict, List


@dataclass
class IntentDecision:
    complexity: str
    route: str
    needs_publish: bool
    needs_approval: bool
    reasons: List[str]

    def to_dict(self) -> Dict[str, object]:
        return {
            "complexity": self.complexity,
            "route": self.route,
            "needs_publish": self.needs_publish,
            "needs_approval": self.needs_approval,
            "reasons": self.reasons,
        }


class IntentClassifier:
    def classify(self, goal: str) -> Dict[str, object]:
        goal = goal.strip()
        needs_approval = any(word in goal for word in ["正式铺货", "确认铺货", "真的铺货", "执行铺货"])
        needs_publish = needs_approval or "铺货" in goal
        multi_step = any(word in goal for word in ["并", "然后", "再", "挑", "找", "推荐"])
        if "店铺" in goal and not needs_publish and not any(word in goal for word in ["找", "推荐", "选品"]):
            decision = IntentDecision("simple", "shop_lookup", False, False, ["shop lookup only"])
        elif needs_publish or multi_step:
            decision = IntentDecision(
                "complex",
                "selection_publish" if needs_publish else "selection",
                needs_publish,
                needs_approval,
                ["multi-step ecommerce workflow"],
            )
        else:
            decision = IntentDecision("simple", "product_search", False, False, ["single read-only task"])
        return decision.to_dict()
