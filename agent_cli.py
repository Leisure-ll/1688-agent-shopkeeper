import argparse
import json
from typing import Any, Dict

from agent.config.settings import AgentSettings
from agent.core.fsm import PlanModeFSM
from agent.planning.planner import HeuristicPlanner, LLMPlanner, plan_to_json
from agent.runtime.app import AgentRuntime, create_runtime


def build_runtime(workspace: str, mock: bool = False) -> AgentRuntime:
    return create_runtime(AgentSettings.from_env(workspace=workspace, mock=mock))


def create_planner(use_llm: bool = False):
    if use_llm:
        from agent.providers.openai_compatible import OpenAICompatibleJSONPlannerProvider

        return LLMPlanner(OpenAICompatibleJSONPlannerProvider())
    return HeuristicPlanner()


def cmd_plan(args: argparse.Namespace) -> None:
    runtime = build_runtime(args.workspace, args.mock)
    planner = create_planner(args.llm)
    memories = runtime.memory.search(args.goal)
    plan = planner.create_plan(args.goal, memories)
    runtime.store.save(plan)
    print(plan_to_json(plan))


def cmd_run(args: argparse.Namespace) -> None:
    runtime = build_runtime(args.workspace, args.mock)
    planner = create_planner(args.llm)
    memories = runtime.memory.search(args.goal)
    plan = planner.create_plan(args.goal, memories)
    fsm = PlanModeFSM(runtime.store, runtime.worker, runtime.hooks)
    result = fsm.run(plan, auto_confirm=args.yes)
    payload = result.to_dict()
    print(json.dumps(payload, ensure_ascii=False, indent=2) if args.json else summary(payload))


def cmd_approve(args: argparse.Namespace) -> None:
    runtime = build_runtime(args.workspace, args.mock)
    approval = runtime.approvals.approve(args.approval_id)
    result = runtime.shopkeeper.publish_real(approval["product_ids"], approval["shop_id"])
    print(json.dumps({"approval": approval, "publish": result}, ensure_ascii=False, indent=2))


def summary(plan: Dict[str, Any]) -> str:
    lines = [f"Plan {plan['id']} status={plan['status']}"]
    for task in plan["tasks"]:
        lines.append(f"- {task['status']}: {task['title']} [{task['tool']}]")
        if task.get("result"):
            lines.append(f"  result: {json.dumps(task['result'], ensure_ascii=False)[:300]}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="1688 vertical ecommerce agent")
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ["plan", "run"]:
        p = sub.add_parser(name)
        p.add_argument("goal")
        p.add_argument("--workspace", default=".agent_data")
        p.add_argument("--mock", action="store_true")
        p.add_argument("--llm", action="store_true")
        p.add_argument("--yes", action="store_true")
        p.add_argument("--json", action="store_true")
        p.set_defaults(func=cmd_plan if name == "plan" else cmd_run)
    p = sub.add_parser("approve")
    p.add_argument("approval_id")
    p.add_argument("--workspace", default=".agent_data")
    p.add_argument("--mock", action="store_true")
    p.set_defaults(func=cmd_approve)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
