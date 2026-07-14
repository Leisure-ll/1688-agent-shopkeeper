import json
import time
from pathlib import Path
from typing import Any, Dict, Optional


class Span:
    def __init__(self, name: str, attrs: Optional[Dict[str, Any]] = None):
        self.name = name
        self.attrs = attrs or {}
        self.start = time.time()
        self.end = None
        self.error = None

    def finish(self, error: Optional[str] = None) -> "Span":
        self.end = time.time()
        self.error = error
        return self

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "attrs": self.attrs,
            "start": self.start,
            "end": self.end,
            "duration_ms": None if self.end is None else int((self.end - self.start) * 1000),
            "error": self.error,
        }


class Observer:
    def start_span(self, name: str, attrs: Optional[Dict[str, Any]] = None) -> Span:
        return Span(name, attrs)

    def end_span(self, span: Span, error: Optional[str] = None) -> None:
        pass


class NoopObserver(Observer):
    pass


class JSONLObserver(Observer):
    def __init__(self, workspace: str = ".agent_data"):
        root = Path(workspace) / "observability"
        root.mkdir(parents=True, exist_ok=True)
        self.path = root / f"trace_{int(time.time() * 1000)}.jsonl"

    def end_span(self, span: Span, error: Optional[str] = None) -> None:
        span.finish(error)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(span.to_dict(), ensure_ascii=False) + "\n")
