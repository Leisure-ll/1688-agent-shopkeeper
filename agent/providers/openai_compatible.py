import json
import os
import urllib.request
from typing import Any, Dict, List

from agent.planning.schemas import planner_schema_hint
from agent.prompts.registry import PromptRegistry
from agent.providers.retry import RetryPolicy


class OpenAICompatibleJSONPlannerProvider:
    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY") or os.environ.get("AGENT_LLM_API_KEY")
        self.base_url = base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.model = model or os.environ.get("AGENT_PLANNER_MODEL", "gpt-4.1-mini")
        self.timeout = int(os.environ.get("AGENT_LLM_TIMEOUT", "30"))
        self.retry = RetryPolicy(attempts=int(os.environ.get("AGENT_LLM_RETRY", "2")))
        self.prompts = PromptRegistry()
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY or AGENT_LLM_API_KEY is required")

    def create_plan(self, goal: str, memories: List[Dict[str, str]]) -> Dict[str, Any]:
        prompt = self.prompts.render(
            "planner",
            schema=json.dumps(planner_schema_hint(), ensure_ascii=False),
            allowed_tools="memory_search, search_products, list_shops, publish_dry_run, request_publish_approval, write_memory",
        )
        return self._json_chat(prompt["text"], {"goal": goal, "memories": memories, "prompt_version": prompt["version"]})

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
        def send() -> Dict[str, Any]:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))

        data = self.retry.run(send)
        return json.loads(data["choices"][0]["message"]["content"])
