#!/usr/bin/env python3
"""Minimal OpenAI-compatible JSON planner provider."""

from __future__ import annotations

import json
import os
from typing import Any, Dict

import requests


class OpenAICompatiblePlannerProvider:
    """Calls an OpenAI-compatible chat completions endpoint for JSON planning."""

    def __init__(self):
        self.base_url = os.environ.get("AGENT_LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        self.api_key = os.environ.get("AGENT_LLM_API_KEY") or os.environ.get("OPENAI_API_KEY", "")
        self.model = os.environ.get("AGENT_LLM_MODEL", "gpt-4o-mini")

    def generate_plan(self, goal: str) -> Dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("AGENT_LLM_API_KEY or OPENAI_API_KEY is not configured")

        prompt = (
            "You are a planner for a 1688 shopkeeper agent. Return ONLY valid JSON.\n"
            "Available tools: search_products, rank_products, list_shops, publish_dry_run, "
            "request_publish_approval, generate_advice, fetch_trend, fetch_opportunities.\n"
            "Rules: produce a DAG task list. Use depends_on as zero-based task indexes. "
            "Never include publish_real directly. For real publishing, use request_publish_approval after publish_dry_run.\n"
            "Schema: {\"name\": string, \"tasks\": [{\"goal\": string, \"tool_name\": string, "
            "\"args\": object, \"depends_on\": number[]}]}\n"
            f"User goal: {goal}"
        )
        resp = requests.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
            },
            timeout=30,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        return json.loads(self._strip_code_fence(content))

    def _strip_code_fence(self, text: str) -> str:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        return cleaned.strip()
