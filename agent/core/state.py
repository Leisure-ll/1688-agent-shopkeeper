from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


@dataclass
class Task:
    id: str
    title: str
    tool: str
    args: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)
    status: str = "pending"
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@dataclass
class Plan:
    id: str
    goal: str
    status: str
    tasks: List[Task]
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    version: int = 1
    drift_count: int = 0
    notes: List[str] = field(default_factory=list)
    session_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "goal": self.goal,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "version": self.version,
            "drift_count": self.drift_count,
            "notes": self.notes,
            "session_id": self.session_id,
            "tasks": [task.__dict__ for task in self.tasks],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Plan":
        return cls(
            id=data["id"],
            goal=data["goal"],
            status=data["status"],
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            version=int(data.get("version", 1)),
            drift_count=int(data.get("drift_count", 0)),
            notes=list(data.get("notes", [])),
            session_id=data.get("session_id", ""),
            tasks=[Task(**task) for task in data.get("tasks", [])],
        )
