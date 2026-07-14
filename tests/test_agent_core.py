import tempfile
import unittest

from agent.core.fsm import PlanModeFSM
from agent.core.hooks import AgentEventHooks
from agent.core.state import Plan, Task
from agent.memory.store import MemoryStore
from agent.memory.writer import MemoryWriter
from agent.persist.plan_store import PlanStore
from agent.planning.planner import HeuristicPlanner, LLMPlanner
from agent.planning.validator import validate_plan_payload
from agent.runtime.worker import AgentWorker
from agent.safety.approval import ApprovalStore
from agent.tools.mock_shopkeeper import MockShopkeeperTools
from agent.tools.registry import ToolRegistry


class AgentCoreTest(unittest.TestCase):
    def runtime(self, tmp):
        memory = MemoryStore(tmp)
        approvals = ApprovalStore(tmp)
        tools = MockShopkeeperTools(tmp)
        registry = ToolRegistry()
        registry.register("search_products", tools.search_products)
        registry.register("list_shops", tools.list_shops)
        registry.register("publish_dry_run", tools.publish_dry_run)
        registry.register("write_memory", lambda kind, content: memory.append(kind, content) or {"ok": True})
        registry.register("memory_search", lambda query, limit=5: {"memories": memory.search(query, limit)})
        registry.register("request_publish_approval", approvals.request_publish)
        hooks = AgentEventHooks()
        return memory, approvals, tools, PlanStore(tmp), AgentWorker(registry, tmp, hooks), hooks

    def test_plan_run_done(self):
        with tempfile.TemporaryDirectory() as tmp:
            memory, _, _, store, worker, hooks = self.runtime(tmp)
            plan = HeuristicPlanner().create_plan("帮我找适合抖店卖的夏季连衣裙，挑5个靠谱的并铺货", [])
            result = PlanModeFSM(store, worker, hooks).run(plan, auto_confirm=True)
            self.assertEqual(result.status, "done")
            self.assertTrue((store.plan_dir(result.id) / "plan.json").exists())
            self.assertIn("Recent selected products", memory.memory_md.read_text(encoding="utf-8"))

    def test_formal_publish_requires_approval(self):
        plan = HeuristicPlanner().create_plan("帮我正式铺货夏季连衣裙", [])
        self.assertIn("request_publish_approval", [task.tool for task in plan.tasks])

    def test_memory_source_and_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            memory = MemoryStore(tmp)
            memory.append("preference", "夏季连衣裙优先看销量和供应商评分")
            self.assertTrue(memory.memory_md.exists())
            self.assertEqual(memory.search("连衣裙")[0]["kind"], "preference")

    def test_llm_planner_validates_valid_payload(self):
        class Provider:
            def create_plan(self, goal, memories):
                return {"tasks": [{"title": "搜索候选商品", "tool": "search_products", "args": {"query": goal}}]}

        plan = LLMPlanner(Provider()).create_plan("找夏季连衣裙", [])
        self.assertEqual(plan.notes, ["llm planner", "schema validated"])
        self.assertEqual(plan.tasks[0].tool, "search_products")

    def test_llm_planner_repairs_invalid_tool(self):
        class Provider:
            def create_plan(self, goal, memories):
                return {"tasks": [{"title": "直接正式铺货", "tool": "publish_real"}]}

            def repair_plan(self, goal, memories, invalid_plan, issues):
                return {"tasks": [{"title": "申请正式铺货审批", "tool": "request_publish_approval"}]}

        plan = LLMPlanner(Provider()).create_plan("帮我正式铺货夏季连衣裙", [])
        self.assertEqual(plan.tasks[0].tool, "request_publish_approval")
        self.assertIn("llm planner repaired", plan.notes)

    def test_llm_planner_falls_back_when_repair_fails(self):
        class Provider:
            def create_plan(self, goal, memories):
                return {"tasks": []}

            def repair_plan(self, goal, memories, invalid_plan, issues):
                return {"tasks": [{"title": "坏计划", "tool": "publish_real"}]}

        plan = LLMPlanner(Provider()).create_plan("帮我正式铺货夏季连衣裙", [])
        self.assertIn("fallback repair planner", plan.notes)
        self.assertIn("request_publish_approval", [task.tool for task in plan.tasks])

    def test_validator_rejects_unknown_tool(self):
        issues = validate_plan_payload({"tasks": [{"title": "坏工具", "tool": "delete_all"}]})
        self.assertTrue(any("tool must be one of" in issue.message for issue in issues))

    def test_dag_executor_respects_dependencies(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, _, _, store, worker, hooks = self.runtime(tmp)
            search = Task("t_search", "搜索候选商品", "search_products", {"query": "夏季连衣裙", "channel": "douyin", "limit": 2})
            shops = Task("t_shops", "查询可用店铺", "list_shops", {"channel": "douyin"})
            publish = Task("t_publish", "铺货预检查", "publish_dry_run", {}, ["t_search", "t_shops"])
            plan = Plan("plan_dag_test", "帮我找夏季连衣裙并铺货", "init", [publish, shops, search])
            result = PlanModeFSM(store, worker, hooks).run(plan, auto_confirm=True)
            self.assertEqual(result.status, "done")
            self.assertEqual(search.status, "done")
            self.assertEqual(shops.status, "done")
            self.assertEqual(publish.status, "done")
            self.assertEqual(publish.result["product_ids"], ["p1004", "p1003"])

    def test_dag_executor_rejects_cycles(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, _, _, store, worker, hooks = self.runtime(tmp)
            a = Task("a", "A", "memory_search", {"query": "x"}, ["b"])
            b = Task("b", "B", "memory_search", {"query": "x"}, ["a"])
            plan = Plan("plan_cycle_test", "循环依赖", "init", [a, b])
            result = PlanModeFSM(store, worker, hooks).run(plan, auto_confirm=True)
            self.assertEqual(result.status, "failed")

    def test_memory_pipeline_extracts_and_dedups_facts(self):
        with tempfile.TemporaryDirectory() as tmp:
            memory = MemoryStore(tmp)
            writer = MemoryWriter(memory)
            first = writer.write("selection", "Recent selected products: [{'id': 'p1001'}, {'id': 'p1002'}]")
            second = writer.write("selection", "Recent selected products: [{'id': 'p1001'}, {'id': 'p1002'}]")
            text = memory.memory_md.read_text(encoding="utf-8")
            self.assertEqual(first["written"], 2)
            self.assertEqual(second["written"], 0)
            self.assertIn("selection.product.p1001", text)
            self.assertTrue((memory.root / "memory_graph.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
