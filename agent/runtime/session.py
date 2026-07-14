import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict

from agent.core.state import new_id
from agent.runtime.workspace import AgentWorkspace


@dataclass
class AgentSession:
    id: str
    goal: str
    workspace: AgentWorkspace


class SessionStore:
    def __init__(self, workspace: AgentWorkspace):
        self.workspace = workspace
        self.workspace.ensure()

    def create(self, goal: str) -> AgentSession:
        session = AgentSession(new_id("session"), goal, self.workspace)
        self.append(session.id, "session.created", {"goal": goal})
        return session

    def append(self, session_id: str, event: str, payload: Dict[str, object]) -> None:
        path = self.path(session_id)
        row = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "session_id": session_id,
            "event": event,
            "payload": payload,
        }
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    def path(self, session_id: str) -> Path:
        self.workspace.sessions_dir().mkdir(parents=True, exist_ok=True)
        return self.workspace.sessions_dir() / f"{session_id}.jsonl"
