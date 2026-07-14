#!/usr/bin/env python3
"""Lightweight observability primitives inspired by Kugelblitz."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import time
import uuid
from typing import Any, Dict, Optional


def _now() -> float:
    return time.time()


class Observer:
    def name(self) -> str:
        raise NotImplementedError

    def start_trace(self, name: str, goal: str) -> "Span":
        raise NotImplementedError


@dataclass
class Span:
    observer: "JSONLObserver"
    trace_id: str
    name: str
    attrs: Dict[str, Any] = field(default_factory=dict)
    parent_id: str = ""
    span_id: str = field(default_factory=lambda: f"span_{uuid.uuid4().hex[:10]}")
    started_at: float = field(default_factory=_now)
    ended_at: float = 0.0

    def start_span(self, name: str, attrs: Optional[Dict[str, Any]] = None) -> "Span":
        child = Span(
            observer=self.observer,
            trace_id=self.trace_id,
            name=name,
            attrs=attrs or {},
            parent_id=self.span_id,
        )
        self.observer.record("span_start", child.to_event())
        return child

    def start_generation(self, attrs: Optional[Dict[str, Any]] = None) -> "Span":
        return self.start_span("generation", attrs or {})

    def set_attributes(self, attrs: Dict[str, Any]) -> None:
        self.attrs.update(attrs)
        self.observer.record("span_update", self.to_event())

    def record_error(self, err: Exception) -> None:
        self.set_attributes({"status": "error", "error": str(err)})

    def end(self) -> None:
        self.ended_at = _now()
        self.observer.record("span_end", self.to_event())

    def to_event(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_id": self.parent_id,
            "name": self.name,
            "attrs": self.attrs,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
        }


class NoopObserver(Observer):
    def name(self) -> str:
        return "noop"

    def start_trace(self, name: str, goal: str) -> Span:
        return NoopSpan()


class NoopSpan:
    def start_span(self, name: str, attrs: Optional[Dict[str, Any]] = None) -> "NoopSpan":
        return self

    def start_generation(self, attrs: Optional[Dict[str, Any]] = None) -> "NoopSpan":
        return self

    def set_attributes(self, attrs: Dict[str, Any]) -> None:
        return None

    def record_error(self, err: Exception) -> None:
        return None

    def end(self) -> None:
        return None


class JSONLObserver(Observer):
    """Persists traces locally as JSONL events.

    This mirrors Kugelblitz's observer abstraction while avoiding a hard
    dependency on Langfuse. A Langfuse exporter can replay these events later.
    """

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.current_file: Optional[Path] = None

    def name(self) -> str:
        return "jsonl"

    def start_trace(self, name: str, goal: str) -> Span:
        trace_id = f"trace_{uuid.uuid4().hex[:10]}"
        self.current_file = self.root / f"{trace_id}.jsonl"
        trace = Span(observer=self, trace_id=trace_id, name=name, attrs={"goal": goal}, parent_id="", span_id=trace_id)
        self.record("trace_start", trace.to_event())
        return trace

    def record(self, event_type: str, body: Dict[str, Any]) -> None:
        if not self.current_file:
            return
        payload = {"type": event_type, "time": _now(), "body": body}
        with self.current_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
