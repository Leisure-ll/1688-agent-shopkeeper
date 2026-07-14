import tempfile
import unittest

from agent.core.fsm import PlanModeFSM
from agent.core.hooks import AgentEventHooks
from agent.memory.store import MemoryStore
from agent.persist.plan_store import PlanStore
from agent.planning.planner import HeuristicPlanner
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


if __name__ == "__main__":
    unittest.main()
