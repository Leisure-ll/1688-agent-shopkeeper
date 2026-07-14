#!/usr/bin/env python3
"""A focused planner that creates plans but does not execute tools."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Protocol

from .state import Plan, Task


CHANNEL_HINTS = {
    "抖店": "douyin",
    "抖音": "douyin",
    "拼多多": "pinduoduo",
    "小红书": "xiaohongshu",
    "淘宝": "taobao",
}


class PlannerProvider(Protocol):
    def generate_plan(self, goal: str) -> Dict[str, Any]:
        ...


class BasePlanner:
    def classify(self, goal: str) -> str:
        raise NotImplementedError

    def create_plan(self, goal: str) -> Plan:
        raise NotImplementedError


class HeuristicPlanner(BasePlanner):
    """Heuristic planner for the interview demo.

    The important design point is separation of concerns: this class only turns
    a user goal into a validated DAG of tasks. Tool calls happen in WorkerAgent.
    """

    def classify(self, goal: str) -> str:
        plan_terms = ["找", "搜", "选品", "铺货", "上架", "趋势", "商机", "日报", "店铺", "推荐"]
        complex_terms = ["并", "然后", "同时", "一键", "挑", "推荐", "铺"]
        if any(term in goal for term in plan_terms) and any(term in goal for term in complex_terms):
            return "plan"
        if len(goal) > 24 and any(term in goal for term in plan_terms):
            return "plan"
        return "direct"

    def create_plan(self, goal: str) -> Plan:
        channel = self._extract_channel(goal)
        query = self._extract_query(goal)
        tasks: List[Task] = []

        if any(term in goal for term in ["商机", "热榜", "机会"]):
            tasks.append(Task(goal="获取当前商机热榜", action="fetch_opportunities", tool_name="fetch_opportunities"))

        if any(term in goal for term in ["趋势", "价格分布"]):
            tasks.append(Task(goal=f"分析「{query}」趋势", action="fetch_trend", tool_name="fetch_trend", args={"query": query}))

        has_search_intent = any(term in goal for term in ["找", "搜", "选品", "推荐", "商品", "货源"])
        if has_search_intent:
            tasks.append(
                Task(
                    goal=f"搜索 1688 商品：{query}",
                    action="search_products",
                    tool_name="search_products",
                    args={"query": query, "channel": channel},
                )
            )
            parent = tasks[-1].id
            tasks.append(
                Task(
                    goal="基于销量、好评率、复购率、揽收率和渠道适配度给出推荐",
                    action="rank_products",
                    tool_name="rank_products",
                    parent_task_ids=[parent],
                )
            )

        if any(term in goal for term in ["店铺", "绑定", "授权", "铺货", "上架"]):
            tasks.append(Task(goal="查询已绑定店铺和授权状态", action="list_shops", tool_name="list_shops"))

        if any(term in goal for term in ["铺货", "上架"]):
            parents = [task.id for task in tasks if task.action in ("search_products", "rank_products", "list_shops")]
            tasks.append(
                Task(
                    goal="铺货前 dry-run 预检查，不执行真实写入",
                    action="publish_dry_run",
                    tool_name="publish_dry_run",
                    parent_task_ids=parents,
                    args={"item_ids": [], "shop_code": ""},
                )
            )

        if any(term in goal for term in ["正式铺货", "确认铺货", "真的铺货", "执行铺货"]):
            parents = [task.id for task in tasks if task.action == "publish_dry_run"]
            tasks.append(
                Task(
                    goal="创建正式铺货的人类审批请求",
                    action="request_publish_approval",
                    tool_name="request_publish_approval",
                    parent_task_ids=parents,
                )
            )

        if has_search_intent:
            parents = [task.id for task in tasks if task.action in ("rank_products", "list_shops", "publish_dry_run", "request_publish_approval")]
            tasks.append(
                Task(
                    goal="根据选品结果、店铺状态和预检查结果生成经营建议",
                    action="generate_advice",
                    tool_name="generate_advice",
                    parent_task_ids=parents,
                )
            )

        if not tasks:
            tasks.append(Task(goal=goal, action="memory_search", tool_name="memory_search", args={"query": goal}))

        plan = Plan(name=f"1688 Agent Plan: {query[:20]}", original_goal=goal, tasks=tasks)
        plan.validate()
        return plan

    def _extract_channel(self, goal: str) -> str:
        for label, channel in CHANNEL_HINTS.items():
            if label in goal:
                return channel
        return ""

    def _extract_query(self, goal: str) -> str:
        cleaned = goal
        for token in ["帮我", "请", "在1688", "1688上", "找一些", "找", "搜索", "搜", "适合", "卖的", "并", "然后", "铺货", "上架"]:
            cleaned = cleaned.replace(token, " ")
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" ，。,.")
        return cleaned[:40] or "热门商品"


class LLMPlanner(BasePlanner):
    """Structured LLM planner adapter.

    The provider is intentionally tiny for interview/demo purposes. A real
    implementation can map this to OpenAI structured outputs, function calling,
    or any internal model gateway.
    """

    def __init__(self, provider: PlannerProvider, fallback: BasePlanner | None = None):
        self.provider = provider
        self.fallback = fallback or HeuristicPlanner()

    def classify(self, goal: str) -> str:
        return "plan"

    def create_plan(self, goal: str) -> Plan:
        try:
            raw = self.provider.generate_plan(goal)
            tasks: List[Task] = []
            id_by_index: Dict[int, str] = {}
            for index, item in enumerate(raw.get("tasks", [])):
                parents = [id_by_index[p] for p in item.get("depends_on", []) if p in id_by_index]
                task = Task(
                    goal=item["goal"],
                    action=item.get("action", item.get("tool_name", "")),
                    tool_name=item["tool_name"],
                    args=item.get("args", {}) or {},
                    parent_task_ids=parents,
                )
                tasks.append(task)
                id_by_index[index] = task.id
            plan = Plan(name=raw.get("name", "LLM generated 1688 plan"), original_goal=goal, tasks=tasks)
            plan.validate()
            return plan
        except Exception:
            return self.fallback.create_plan(goal)


class JSONPlannerProvider:
    """Small provider useful for tests and demos."""

    def __init__(self, plan_json: str):
        self.plan_json = plan_json

    def generate_plan(self, goal: str) -> Dict[str, Any]:
        return json.loads(self.plan_json)


Planner = HeuristicPlanner
