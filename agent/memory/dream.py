from typing import Iterable, List

from agent.memory.fact import MemoryFact


class MemoryDreamer:
    def reflect(self, facts: Iterable[MemoryFact]) -> str:
        product_ids: List[str] = []
        for fact in facts:
            if fact.key.startswith("selection.product."):
                product_ids.append(fact.key.rsplit(".", 1)[-1])
        if len(product_ids) < 3:
            return ""
        joined = ", ".join(product_ids)
        return (
            "Selection reflection: recent plans repeatedly selected products "
            f"{joined}. Keep prioritizing products with strong sales, stable supplier score, "
            "and channel fit before publishing."
        )
