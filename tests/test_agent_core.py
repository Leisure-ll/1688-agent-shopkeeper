import tempfile
import unittest

from agent.core.fsm import PlanModeFSM
from agent.core.hooks import AgentEventHooks
from agent.memory.store import MemoryStore
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


if __name__ == "__main__":
    unittest.main()
