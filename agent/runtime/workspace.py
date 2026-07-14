from pathlib import Path


class AgentWorkspace:
    def __init__(self, root: str = ".agent_data"):
        self.root = Path(root)

    def ensure(self) -> None:
        for path in [self.root, self.memory_dir(), self.sessions_dir(), self.plans_dir(), self.observability_dir()]:
            path.mkdir(parents=True, exist_ok=True)

    def memory_dir(self) -> Path:
        return self.root / "memory"

    def sessions_dir(self) -> Path:
        return self.root / "sessions"

    def plans_dir(self) -> Path:
        return self.root / "plans"

    def approvals_dir(self) -> Path:
        return self.root / "approvals"

    def observability_dir(self) -> Path:
        return self.root / "observability"

    def tool_audit_path(self) -> Path:
        return self.observability_dir() / "tool_audit.jsonl"
