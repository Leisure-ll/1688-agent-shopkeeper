import hashlib
import re
from typing import List

from agent.memory.fact import MemoryFact


class MemoryExtractor:
    def extract(self, kind: str, content: str) -> List[MemoryFact]:
        content = content.strip()
        if not content:
            return []
        product_ids = sorted(set(re.findall(r"p\d+", content)))
        if product_ids:
            return [
                MemoryFact(
                    key=f"selection.product.{product_id}",
                    value=f"selected in recent plan: {product_id}",
                    kind=kind,
                    confidence=0.8,
                )
                for product_id in product_ids
            ]
        digest = hashlib.sha1(content.encode("utf-8")).hexdigest()[:10]
        return [MemoryFact(key=f"{kind}.{digest}", value=content, kind=kind, confidence=0.7)]
