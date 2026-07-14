from dataclasses import dataclass
from typing import Any, Dict, List


ALLOWED_PLANNER_TOOLS = {
    "memory_search",
    "search_products",
    "list_shops",
    "publish_dry_run",
    "request_publish_approval",
    "write_memory",
}

FORBIDDEN_PLANNER_TOOLS = {
    "publish_real",
}


@dataclass
class PlanValidationIssue:
    path: str
    message: str

    def to_dict(self) -> Dict[str, str]:
        return {"path": self.path, "message": self.message}


def planner_schema_hint() -> Dict[str, Any]:
    return {
        "type": "object",
        "required": ["tasks"],
        "properties": {
            "id": {"type": "string", "optional": True},
            "tasks": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "required": ["title", "tool"],
                    "properties": {
                        "id": {"type": "string", "optional": True},
                        "title": {"type": "string"},
                        "tool": {"enum": sorted(ALLOWED_PLANNER_TOOLS)},
                        "args": {"type": "object", "optional": True},
                        "depends_on": {"type": "array[string]", "optional": True},
                    },
                },
            },
        },
    }


def issues_to_prompt(issues: List[PlanValidationIssue]) -> str:
    return "\n".join(f"- {issue.path}: {issue.message}" for issue in issues)
