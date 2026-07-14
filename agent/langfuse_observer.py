#!/usr/bin/env python3
"""Langfuse observer for hook-driven agent traces."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
import time
import uuid
from typing import Any, Dict, List

import requests

from .observability import Observer, Span


def _iso(ts: float = None) -> str:
    return datetime.fromtimestamp(ts or time.time(), tz=timezone.utc).isoformat()


class LangfuseObserver(Observer):
    """Minimal Langfuse ingestion observer.

    Env:
      LANGFUSE_HOST=https://cloud.langfuse.com
      LANGFUSE_PUBLIC_KEY=...
      LANGFUSE_SECRET_KEY=...
    """

    def __init__(self, host: str = "", public_key: str = "", secret_key: str = ""):
        self.host = (host or os.environ.get("LANGFUSE_HOST") or os.environ.get("LANGFUSE_BASE_URL") or "").rstrip("/")
        self.public_key = public_key or os.environ.get("LANGFUSE_PUBLIC_KEY", "")
        self.secret_key = secret_key or os.environ.get("LANGFUSE_SECRET_KEY", "")
        self.batch: List[Dict[str, Any]] = []

    def name(self) -> str:
        return "langfuse"

    def enabled(self) -> bool:
        return bool(self.host and self.public_key and self.secret_key)

    def start_trace(self, name: str, goal: str) -> Span:
        trace_id = f"trace_{uuid.uuid4().hex[:10]}"
        trace = Span(observer=self, trace_id=trace_id, name=name, attrs={"goal": goal}, parent_id="", span_id=trace_id)
        self.record("trace_start", trace.to_event())
        return trace

    def record(self, event_type: str, body: Dict[str, Any]) -> None:
        if not self.enabled():
            return
        converted = self._convert_event(event_type, body)
        if converted:
            self.batch.append(converted)

    def flush(self) -> None:
        if not self.enabled() or not self.batch:
            return
        batch = self.batch
        self.batch = []
        traces = [event for event in batch if event["type"] == "trace-create"]
        rest = [event for event in batch if event["type"] != "trace-create"]
        if traces:
            self._send(traces)
        if rest:
            self._send(rest)

    def _send(self, events: List[Dict[str, Any]]) -> None:
        resp = requests.post(
            f"{self.host}/api/public/ingestion",
            auth=(self.public_key, self.secret_key),
            headers={"Content-Type": "application/json"},
            data=json.dumps({"batch": events}, ensure_ascii=False).encode("utf-8"),
            timeout=10,
        )
        resp.raise_for_status()

    def _convert_event(self, event_type: str, body: Dict[str, Any]) -> Dict[str, Any]:
        attrs = body.get("attrs", {}) or {}
        ts = _iso(body.get("started_at") or time.time())
        trace_id = body["trace_id"]
        span_id = body["span_id"]
        parent_id = body.get("parent_id") or ""

        if event_type == "trace_start":
            payload = {
                "id": trace_id,
                "name": body.get("name", "agent.run"),
                "input": attrs.get("goal", ""),
                "startTime": ts,
                "metadata": {"source": "1688-shopkeeper-agent"},
            }
            return self._event("trace-create", trace_id, payload)

        if event_type == "span_start":
            payload = {
                "id": span_id,
                "name": body.get("name", "span"),
                "traceId": trace_id,
                "startTime": ts,
                "metadata": attrs,
            }
            if parent_id and parent_id != trace_id:
                payload["parentObservationId"] = parent_id
            return self._event("span-create", span_id, payload)

        if event_type in ("span_update", "span_end"):
            payload = {
                "id": span_id,
                "traceId": trace_id,
                "metadata": attrs,
            }
            if event_type == "span_end":
                payload["endTime"] = _iso(body.get("ended_at") or time.time())
            return self._event("span-update", span_id + "-" + event_type, payload)

        return {}

    def _event(self, event_type: str, event_id: str, body: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "type": event_type,
            "id": event_id,
            "timestamp": _iso(),
            "body": body,
        }
