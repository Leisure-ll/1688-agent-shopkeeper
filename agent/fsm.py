#!/usr/bin/env python3
"""Plan-mode finite-state machine for the 1688 shopkeeper agent."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .memory import LongTermMemory
from .llm_provider import OpenAICompatiblePlannerProvider
from .persist import AgentStore
from .approval import ApprovalStore
from .planner import BasePlanner, LLMPlanner, Planner
from .reviewer import Reviewer
from . import shopkeeper_tools
from .mock_shopkeeper_tools import MockShopkeeperTools
from .observability import JSONLObserver, NoopObserver
from .langfuse_observer import LangfuseObserver
from .instrument import HookInstrument
from .state import AgentRunResult, Plan, PlanState, TaskStatus
from .subagent import SubAgentManager
from .tooling import ToolRegistry, ToolSpec, tools_for_state, worker_tools


class ShopkeeperAgent:
    def __init__(self, workspace: Union[str, Path] = ".agent_data", mock_mode: bool = False, planner: Optional[BasePlanner] = None):
        self.store = AgentStore(workspace)
        self.memory = LongTermMemory(self.store.memory_path(), self.store.graph_path())
        self.approvals = ApprovalStore(self.store.approval_dir())
        self.observer = NoopObserver()
        self.instrument = HookInstrument(self._build_observer())
        self.event_hooks = self.instrument.hooks()
        self.planner = planner or self._default_planner()
        self.reviewer = Reviewer()
        self.mock_mode = mock_mode
        self.tools = self._build_tools()
        self.subagents = SubAgentManager(self.tools, self.memory, self.store.subagent_trace_dir())

    def _default_planner(self) -> BasePlanner:
        if os.environ.get("AGENT_PLANNER", "").lower() == "llm":
            return LLMPlanner(OpenAICompatiblePlannerProvider(), fallback=Planner())
        return Planner()

    def _build_observer(self):
        wants_langfuse = os.environ.get("AGENT_OBSERVER", "").lower() == "langfuse"
        has_langfuse_config = bool(os.environ.get("LANGFUSE_PUBLIC_KEY") and os.environ.get("LANGFUSE_SECRET_KEY"))
        if wants_langfuse or has_langfuse_config:
            observer = LangfuseObserver()
            if observer.enabled():
                return observer
        return JSONLObserver(self.store.observability_dir())

    def plan(self, goal: str) -> AgentRunResult:
        trace = self.observer.start_trace("agent.plan", goal)
        if self.event_hooks.on_run_start:
            self.event_hooks.on_run_start("agent.plan", goal)
        span = trace.start_span("planner.create_plan", {"mode": type(self.planner).__name__})
        try:
            plan = self.planner.create_plan(goal)
            if self.event_hooks.on_plan_created:
                self.event_hooks.on_plan_created(plan.id, len(plan.tasks))
            span.set_attributes({"plan_id": plan.id, "task_count": len(plan.tasks)})
            plan.state = PlanState.CONFIRMED
            self.store.save_plan(plan, reason="plan_created")
            markdown = self._format_plan(plan)
            trace.set_attributes({"state": PlanState.CONFIRMED.value, "success": True})
            if self.event_hooks.on_run_end:
                self.event_hooks.on_run_end(PlanState.CONFIRMED.value, True)
            return AgentRunResult(True, PlanState.CONFIRMED, markdown, {"tool_whitelist": self._whitelist_summary()}, plan)
        except Exception as exc:
            span.record_error(exc)
            trace.record_error(exc)
            if self.event_hooks.on_error:
                self.event_hooks.on_error("agent.plan", exc)
            if self.event_hooks.on_run_end:
                self.event_hooks.on_run_end(PlanState.FAILED.value, False)
            raise
        finally:
            span.end()
            trace.end()

    def run(self, goal: str, auto_confirm: bool = False, max_cycles: int = 12) -> AgentRunResult:
        trace = self.observer.start_trace("agent.run", goal)
        if self.event_hooks.on_run_start:
            self.event_hooks.on_run_start("agent.run", goal)
        state = PlanState.INTENT
        plan: Optional[Plan] = None
        scratch: Dict[str, Any] = {}
        recent_activity: List[str] = []

        def finish(result: AgentRunResult) -> AgentRunResult:
            trace.set_attributes({"state": result.state.value, "success": result.success})
            trace.end()
            if self.event_hooks.on_run_end:
                self.event_hooks.on_run_end(result.state.value, result.success)
            return result

        for _ in range(max_cycles):
            if state == PlanState.INTENT:
                trace.start_span("state.intent", {"goal": goal}).end()
                mode = self.planner.classify(goal)
                if self.event_hooks.on_state_transition:
                    self.event_hooks.on_state_transition(PlanState.INTENT.value, PlanState.INIT.value if mode == "plan" else PlanState.DIRECT.value)
                state = PlanState.INIT if mode == "plan" else PlanState.DIRECT
                continue

            if state == PlanState.DIRECT:
                span = trace.start_span("planner.create_direct_plan", {"mode": type(self.planner).__name__})
                plan = self.planner.create_plan(goal)
                if self.event_hooks.on_plan_created:
                    self.event_hooks.on_plan_created(plan.id, len(plan.tasks))
                span.set_attributes({"plan_id": plan.id, "task_count": len(plan.tasks)})
                span.end()
                self.store.save_plan(plan, reason="direct_plan_created")
                state = PlanState.DOING
                continue

            if state == PlanState.INIT:
                span = trace.start_span("planner.create_plan", {"mode": type(self.planner).__name__})
                plan = self.planner.create_plan(goal)
                if self.event_hooks.on_plan_created:
                    self.event_hooks.on_plan_created(plan.id, len(plan.tasks))
                span.set_attributes({"plan_id": plan.id, "task_count": len(plan.tasks)})
                span.end()
                self.store.save_plan(plan, reason="plan_created")
                state = PlanState.CONFIRMED
                continue

            if state == PlanState.CONFIRMED:
                if not auto_confirm:
                    assert plan is not None
                    plan.state = PlanState.CONFIRMED
                    self.store.save_plan(plan, reason="awaiting_confirmation")
                    return finish(AgentRunResult(
                        True,
                        PlanState.CONFIRMED,
                        self._format_plan(plan) + "\n\n计划已生成。加 `--yes` 才会执行工具。",
                        {"tool_whitelist": self._whitelist_summary()},
                        plan,
                    ))
                assert plan is not None
                plan.state = PlanState.DOING
                self.store.save_plan(plan, reason="plan_confirmed")
                state = PlanState.DOING
                continue

            if state == PlanState.DOING:
                assert plan is not None
                ready = plan.ready_tasks()
                if not ready:
                    state = PlanState.DONE if plan.is_complete() else PlanState.FAILED
                    continue

                for task in ready:
                    if "worker_spawn" not in tools_for_state(PlanState.DOING):
                        return finish(AgentRunResult(False, PlanState.FAILED, "doing 状态没有 worker_spawn 权限。", {}, plan))
                    task_span = trace.start_span("subagent.spawn", {"task_id": task.id, "tool": task.tool_name, "goal": task.goal})
                    updated = self.subagents.spawn(task, plan.original_goal, scratch)
                    if self.event_hooks.on_subagent_spawned:
                        self.event_hooks.on_subagent_spawned(
                            updated.id,
                            updated.tool_name,
                            updated.status.value,
                            bool(updated.result.get("success")) if isinstance(updated.result, dict) else False,
                        )
                    if self.event_hooks.on_task_updated:
                        self.event_hooks.on_task_updated(updated.id, updated.status.value, updated.finished_reason)
                    if self.event_hooks.on_tool_call_end and isinstance(updated.result, dict):
                        self.event_hooks.on_tool_call_end(updated.tool_name, updated.result)
                    task_span.set_attributes({"status": updated.status.value, "result_success": updated.result.get("success") if isinstance(updated.result, dict) else None})
                    task_span.end()
                    self._fold_task_result(updated, scratch)
                    recent_activity.append(f"{updated.goal} {updated.action} {updated.finished_reason}")
                    self.store.save_plan(plan, reason=f"task_{updated.status.value}:{updated.id}")

                    if updated.status == TaskStatus.FAILED and self._try_recover_task(updated):
                        self.store.save_plan(plan, reason=f"task_recovered:{updated.id}")
                        continue

                    review = self.reviewer.review(plan.original_goal, plan, recent_activity[-4:])
                    if review.drift:
                        rolled_back = self._rollback_one_version(plan, review.reason)
                        plan = rolled_back or plan
                        state = PlanState.UPDATING
                        break

                if state == PlanState.UPDATING:
                    continue
                if plan.has_failure():
                    state = PlanState.UPDATING
                    continue
                if plan.is_complete():
                    state = PlanState.DONE
                continue

            if state == PlanState.UPDATING:
                assert plan is not None
                plan.state = PlanState.UPDATING
                self.store.save_plan(plan, reason="needs_replan")
                return finish(AgentRunResult(
                    False,
                    PlanState.UPDATING,
                    "执行中出现失败或目标漂移，计划已进入 updating。请查看 checkpoint 后调整计划。",
                    {"scratch": scratch},
                    plan,
                ))

            if state == PlanState.DONE:
                assert plan is not None
                plan.state = PlanState.DONE
                self.store.save_plan(plan, reason="plan_done")
                self.memory.store("episodic", plan.id, f"Completed goal: {goal}", confidence=0.8)
                return finish(AgentRunResult(True, PlanState.DONE, self._format_summary(plan, scratch), {"scratch": scratch}, plan))

            if state == PlanState.FAILED:
                assert plan is not None
                plan.state = PlanState.FAILED
                self.store.save_plan(plan, reason="plan_failed")
                return finish(AgentRunResult(False, PlanState.FAILED, self._format_summary(plan, scratch), {"scratch": scratch}, plan))

        result = AgentRunResult(False, state, "状态机超过最大循环次数，已停止。", {"scratch": scratch}, plan)
        return finish(result)

    def _build_tools(self) -> ToolRegistry:
        registry = ToolRegistry()
        tools_module = MockShopkeeperTools(self.store.root / "mock_catalog.sqlite") if self.mock_mode else shopkeeper_tools
        registry.register(ToolSpec("search_products", "Search 1688 products", tools_module.search_products))
        registry.register(ToolSpec("rank_products", "Rank searched products", lambda products: self._rank_products_tool(products)))
        registry.register(ToolSpec("product_detail", "Fetch product detail", tools_module.product_detail))
        registry.register(ToolSpec("list_shops", "List bound shops", tools_module.list_shops))
        registry.register(ToolSpec("fetch_trend", "Fetch market trend", tools_module.fetch_trend))
        registry.register(ToolSpec("fetch_opportunities", "Fetch opportunity board", tools_module.fetch_opportunities))
        registry.register(ToolSpec("shop_daily", "Fetch shop daily report", tools_module.shop_daily))
        registry.register(ToolSpec("publish_dry_run", "Preflight publish without write", tools_module.publish_dry_run, risk="write_preview"))
        registry.register(ToolSpec("publish_real", "Execute approved publish", tools_module.publish_real, risk="write"))
        registry.register(ToolSpec("request_publish_approval", "Create a human approval request for publish_real", lambda item_ids, shop_code: self._request_publish_approval_tool(item_ids, shop_code)))
        registry.register(ToolSpec("generate_advice", "Generate business advice from selected products", lambda products, shops=None, publish=None: self._generate_advice_tool(products, shops or [], publish or {})))
        registry.register(ToolSpec("worker_spawn", "Spawn an isolated subagent", lambda: {"success": True, "markdown": "worker spawned", "data": {}}))
        registry.register(ToolSpec("memory_search", "Search MEMORY.md", lambda query, limit=5: self._memory_search(query, limit)))
        registry.register(ToolSpec("memory_store", "Store a MEMORY.md fact", lambda section, key, value: self._memory_store(section, key, value)))
        return registry

    def _memory_search(self, query: str, limit: int = 5) -> Dict[str, Any]:
        items = self.memory.search(query, limit=limit)
        return {
            "success": True,
            "markdown": "\n".join(f"- {item.section}/{item.key}: {item.value}" for item in items) or "未命中长期记忆。",
            "data": {"items": [item.__dict__ for item in items]},
        }

    def _memory_store(self, section: str, key: str, value: str) -> Dict[str, Any]:
        item = self.memory.store(section, key, value)
        return {"success": True, "markdown": f"已写入长期记忆：{section}/{key}", "data": item.__dict__}

    def _fold_task_result(self, task, scratch: Dict[str, Any]) -> None:
        data = task.result.get("data", {}) if isinstance(task.result, dict) else {}
        if task.action == "search_products":
            products = data.get("products", [])
            scratch["products"] = products
            scratch["search_data_id"] = data.get("data_id", "")
        elif task.action == "rank_products":
            scratch["selected_products"] = data.get("selected_products", [])
        elif task.action == "list_shops":
            scratch["shops"] = data.get("shops", [])
        elif task.action == "publish_dry_run":
            scratch["publish_dry_run"] = task.result
        elif task.action == "generate_advice":
            scratch["advice"] = data.get("advice", "")
        elif task.action == "request_publish_approval":
            scratch["approval"] = data

    def _rank_products(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        def score_and_reasons(product: Dict[str, Any]) -> tuple:
            stats = product.get("stats", {}) or {}
            sales = float(stats.get("last30DaysSales") or 0)
            good = float(stats.get("goodRates") or 0)
            repurchase = float(stats.get("repurchaseRate") or 0)
            collection = float(stats.get("collectionRate24h") or 0)
            downstream = float(stats.get("downstreamOffer") or 0)
            score = sales * 0.4 + good * 100 + repurchase * 80 + collection * 50 - min(downstream, 500) * 0.03
            reasons = []
            if sales >= 3000:
                reasons.append("近30天销量高")
            if good >= 0.97:
                reasons.append("好评率高")
            if repurchase >= 0.18:
                reasons.append("复购表现好")
            if collection >= 0.88:
                reasons.append("24h揽收率稳定")
            if downstream >= 200:
                reasons.append("铺货数偏高，注意竞争")
            return score, reasons or ["适合小批量测款"]

        ranked = []
        for product in products:
            score, reasons = score_and_reasons(product)
            enriched = dict(product)
            enriched["ranking_score"] = round(score, 2)
            enriched["reasons"] = reasons
            ranked.append(enriched)
        return sorted(ranked, key=lambda item: item["ranking_score"], reverse=True)

    def _try_recover_task(self, task) -> bool:
        markdown = ""
        if isinstance(task.result, dict):
            markdown = task.result.get("markdown", "")
        if "AK 未配置" in markdown or "签名无效" in markdown:
            task.finished_reason = "needs_ak_config"
            return False
        if task.action == "search_products" and "未找到" in markdown and int(task.args.get("_retry_count", 0)) < 1:
            original = str(task.args.get("query", ""))
            fallback = self._broaden_query(original)
            task.args["query"] = fallback
            task.args["_retry_count"] = int(task.args.get("_retry_count", 0)) + 1
            task.status = TaskStatus.PENDING
            task.result = {}
            task.finished_reason = f"retry with broadened query: {fallback}"
            return True
        return False

    def _broaden_query(self, query: str) -> str:
        for keyword in ["连衣裙", "女装", "收纳", "防晒", "户外", "夏季"]:
            if keyword in query:
                return keyword
        parts = [part for part in query.replace("，", " ").replace(",", " ").split() if len(part) >= 2]
        return parts[0] if parts else query

    def _rank_products_tool(self, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        selected = self._rank_products(products)[:5]
        markdown = "未找到可排序商品。" if not selected else "\n".join(
            f"{idx}. {item.get('title')} - ¥{item.get('price')} ({item.get('id')})"
            for idx, item in enumerate(selected, 1)
        )
        return {"success": bool(selected), "markdown": markdown, "data": {"selected_products": selected}}

    def _generate_advice_tool(
        self,
        products: List[Dict[str, Any]],
        shops: List[Dict[str, Any]],
        publish: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not products:
            return {"success": False, "markdown": "没有可用商品，无法生成经营建议。", "data": {"advice": ""}}

        top = products[0]
        authorized_shops = [shop for shop in shops if shop.get("is_authorized")]
        publish_ok = bool(publish.get("success"))
        sales = (top.get("stats") or {}).get("last30DaysSales", "-")
        price = top.get("price", "-")
        shop_hint = "可直接进入铺货预检查" if authorized_shops else "需要先绑定或授权店铺"
        publish_hint = "预检查已通过，建议小批量测款" if publish_ok else "建议先完成铺货预检查"
        advice = (
            f"优先测试「{top.get('title')}」，参考进货价 ¥{price}，30天销量 {sales}。"
            f"{shop_hint}；{publish_hint}。"
            "首轮控制 2-3 个款，观察点击率、转化率和售后反馈，再扩大 SKU。"
        )
        return {"success": True, "markdown": advice, "data": {"advice": advice}}

    def _request_publish_approval_tool(self, item_ids: List[str], shop_code: str) -> Dict[str, Any]:
        if not item_ids or not shop_code:
            return {"success": False, "markdown": "缺少商品或店铺，无法创建审批。", "data": {}}
        req = self.approvals.create("publish_real", item_ids=item_ids, shop_code=shop_code)
        if self.event_hooks.on_approval_created:
            self.event_hooks.on_approval_created(req.id, req.action)
        return {
            "success": True,
            "markdown": f"已创建正式铺货审批：{req.id}。审批通过后才会执行真实铺货。",
            "data": {"approval_id": req.id, "status": req.status, "item_ids": item_ids, "shop_code": shop_code},
        }

    def approve(self, approval_id: str) -> Dict[str, Any]:
        trace = self.observer.start_trace("agent.approve", approval_id)
        span = trace.start_span("approval.execute", {"approval_id": approval_id})
        req = self.approvals.get(approval_id)
        if not req:
            result = {"success": False, "markdown": f"审批不存在：{approval_id}", "data": {}}
            span.set_attributes({"status": "missing"})
            span.end()
            trace.set_attributes({"success": False})
            trace.end()
            return result
        if req.status != "pending":
            result = {"success": False, "markdown": f"审批状态不是 pending：{req.status}", "data": {"status": req.status}}
            span.set_attributes({"status": req.status})
            span.end()
            trace.set_attributes({"success": False})
            trace.end()
            return result
        result = self.tools.call("publish_real", ["publish_real"], item_ids=req.item_ids, shop_code=req.shop_code)
        approved = self.approvals.approve(approval_id, result)
        payload = {"success": result.get("success", False), "markdown": result.get("markdown", ""), "data": {"approval": approved.__dict__, "result": result}}
        span.set_attributes({"status": approved.status, "success": payload["success"]})
        span.end()
        trace.set_attributes({"success": payload["success"]})
        trace.end()
        return payload

    def _rollback_one_version(self, plan: Plan, reason: str) -> Optional[Plan]:
        if plan.version <= 1:
            return None
        checkpoint = self.store.load_checkpoint(plan.id, plan.version - 1)
        if not checkpoint:
            return None
        restored = Plan.from_dict(checkpoint.plan)
        restored.state = PlanState.UPDATING
        restored.finished_reason = f"drift: {reason}"
        self.store.save_plan(restored, reason="rollback_goal_drift")
        return restored

    def _format_plan(self, plan: Plan) -> str:
        lines = [f"## Plan: {plan.name}", "", f"目标：{plan.original_goal}", ""]
        for idx, task in enumerate(plan.tasks, 1):
            deps = f" deps={','.join(task.parent_task_ids)}" if task.parent_task_ids else ""
            lines.append(f"{idx}. [{task.status.value}] {task.goal} -> `{task.tool_name}`{deps}")
        return "\n".join(lines)

    def _format_summary(self, plan: Plan, scratch: Dict[str, Any]) -> str:
        lines = [self._format_plan(plan), "", "## 执行摘要"]
        if scratch.get("selected_products"):
            lines.append("")
            lines.append("推荐商品 TOP 5：")
            for idx, product in enumerate(scratch["selected_products"], 1):
                lines.append(f"{idx}. {product.get('title')} - ¥{product.get('price')} ({product.get('id')})")
        if scratch.get("shops"):
            lines.append("")
            lines.append(f"已获取店铺数：{len(scratch['shops'])}")
        if scratch.get("publish_dry_run"):
            lines.append("")
            lines.append("铺货 dry-run 已完成，未执行真实写入。")
        return "\n".join(lines)

    def _whitelist_summary(self) -> Dict[str, List[str]]:
        summary = {state.value: tools for state, tools in sorted(tools_for_state_map().items(), key=lambda x: x[0].value)}
        summary["subagent_worker"] = worker_tools()
        return summary


def tools_for_state_map() -> Dict[PlanState, List[str]]:
    return {state: tools_for_state(state) for state in PlanState}
