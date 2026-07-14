#!/usr/bin/env python3
"""CLI entry for the agent-mode 1688 shopkeeper demo."""

from __future__ import annotations

import argparse
import json
import sys

from agent import ShopkeeperAgent


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="1688 shopkeeper agent demo")
    parser.add_argument("command", choices=["plan", "run", "approve"], help="plan, run, or approve a pending write action")
    parser.add_argument("goal", nargs="?", help="natural-language goal, or approval_id for approve")
    parser.add_argument("--workspace", default=".agent_data", help="agent data workspace")
    parser.add_argument("--yes", action="store_true", help="auto-confirm generated plan")
    parser.add_argument("--mock", action="store_true", help="use mock 1688 tools for local demos")
    parser.add_argument("--json", action="store_true", help="print full JSON result")
    args = parser.parse_args()

    agent = ShopkeeperAgent(workspace=args.workspace, mock_mode=args.mock)
    if args.command == "approve":
        if not args.goal:
            parser.error("approve requires approval_id")
        payload = agent.approve(args.goal)
        print(json.dumps(payload, ensure_ascii=False, indent=2) if args.json else payload.get("markdown", ""))
        return

    if not args.goal:
        parser.error(f"{args.command} requires goal")
    result = agent.plan(args.goal) if args.command == "plan" else agent.run(args.goal, auto_confirm=args.yes)

    if args.json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(result.markdown)


if __name__ == "__main__":
    main()
