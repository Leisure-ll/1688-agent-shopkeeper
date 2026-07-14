import json
import os
import urllib.request
from typing import Any, Dict, List

from agent.planning.schemas import planner_schema_hint


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
            "Allowed tools: memory_search, search_products, list_shops, publish_dry_run, request_publish_approval, write_memory. "
            "Never use publish_real. Follow this schema: "
            + json.dumps(planner_schema_hint(), ensure_ascii=False)
        )
        return self._json_chat(prompt, {"goal": goal, "memories": memories})

    def repair_plan(
        self,
        goal: str,
        memories: List[Dict[str, str]],
        invalid_plan: Dict[str, Any],
        issues: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        prompt = (
            "Repair the invalid 1688 ecommerce agent plan. Return JSON only. "
            "Do not execute tools. Never use publish_real. Keep the user goal intact. "
            "Schema: "
            + json.dumps(planner_schema_hint(), ensure_ascii=False)
            + "\nValidation issues:\n"
            + "\n".join(f"- {issue.get('path')}: {issue.get('message')}" for issue in issues)
        )
        return self._json_chat(prompt, {"goal": goal, "memories": memories, "invalid_plan": invalid_plan})

    def _json_chat(self, system_prompt: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
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
