import os
from dataclasses import dataclass


@dataclass
class AgentSettings:
    workspace: str = ".agent_data"
    mock: bool = False
    observer: str = "jsonl"
    planner: str = "heuristic"

    @classmethod
    def from_env(cls, workspace: str = ".agent_data", mock: bool = False, planner: str = "heuristic") -> "AgentSettings":
        return cls(
            workspace=workspace,
            mock=mock,
            observer=os.environ.get("AGENT_OBSERVER", "jsonl"),
            planner=planner,
        )
