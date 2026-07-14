import json
import os
import urllib.request
from typing import Any, Dict, List


class OpenAICompatibleJSONPlannerProvider:
    def __init__(self):
        self.api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("AGENT_LLM_API_KEY")
        self.base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.model = os.environ.get("AGENT_PLANNER_MODEL", "gpt-4.1-mini")
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY or AGENT_LLM_API_KEY is required")

    def create_plan(self, goal: str, memories: List[Dict[str, str]]) -> Dict[str, Any]:
        prompt = (
            "You are a planner for a 1688 ecommerce agent. Return JSON only with a tasks array. "
            "Allowed tools: memory_search, search_products, list_shops, publish_dry_run, request_publish_approval, write_memory."
        )
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": json.dumps({"goal": goal, "memories": memories}, ensure_ascii=False)},
            ],
            "response_format": {"type": "json_object"},
        }
        req = urllib.request.Request(
            f"{self.base_url.rstrip('/')}/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return json.loads(data["choices"][0]["message"]["content"])
