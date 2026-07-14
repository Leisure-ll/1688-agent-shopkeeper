#!/usr/bin/env python3

import tempfile
import unittest
from pathlib import Path

from agent import ShopkeeperAgent
from agent.memory import LongTermMemory
from agent.persist import AgentStore
from agent.planner import JSONPlannerProvider, LLMPlanner, Planner
from agent.subagent import SubAgentManager
from agent.state import PlanState
from agent.tooling import ToolRegistry, ToolSpec, tools_for_state, worker_tools


class AgentCoreTests(unittest.TestCase):
    def test_planner_creates_search_and_rank_dag(self):
        plan = Planner().create_plan("帮我找适合抖店卖的夏季连衣裙，挑5个靠谱的")
        self.assertEqual(["search_products", "rank_products", "generate_advice"], [task.tool_name for task in plan.tasks])
        self.assertEqual([plan.tasks[0].id], plan.tasks[1].parent_task_ids)
        plan.validate()

    def test_tool_whitelist_blocks_business_tools_in_init(self):
        self.assertIn("plan_create", tools_for_state(PlanState.INIT))
        self.assertNotIn("search_products", tools_for_state(PlanState.INIT))
        self.assertNotIn("search_products", tools_for_state(PlanState.DOING))
        self.assertIn("worker_spawn", tools_for_state(PlanState.DOING))
        self.assertIn("search_products", worker_tools())

    def test_checkpoint_is_written_on_save(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = AgentStore(tmp)
            plan = Planner().create_plan("帮我找夏季连衣裙")
            cp = store.save_plan(plan, reason="test")
            self.assertEqual(1, cp.version)
            self.assertTrue((Path(tmp) / "plans" / plan.id / "checkpoints" / "1.json").exists())

    def test_memory_md_is_authoritative_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            memory = LongTermMemory(Path(tmp) / "MEMORY.md", Path(tmp) / "memory_graph.jsonl")
            memory.store("prefs", "target_channel", "douyin")
            reloaded = LongTermMemory(Path(tmp) / "MEMORY.md", Path(tmp) / "memory_graph.jsonl")
            result = reloaded.search("douyin")
            self.assertEqual("target_channel", result[0].key)

    def test_subagent_spawn_writes_isolated_trace(self):
        with tempfile.TemporaryDirectory() as tmp:
            memory = LongTermMemory(Path(tmp) / "MEMORY.md", Path(tmp) / "memory_graph.jsonl")
            registry = ToolRegistry()
            registry.register(
                ToolSpec(
                    "rank_products",
                    "rank",
                    lambda products: {"success": True, "markdown": "ranked", "data": {"selected_products": products}},
                )
            )
            task = Planner().create_plan("帮我找夏季连衣裙").tasks[1]
            manager = SubAgentManager(registry, memory, Path(tmp) / "subagents")
            manager.spawn(task, "帮我找夏季连衣裙", {"products": [{"id": "1", "title": "裙子"}]})
            traces = list((Path(tmp) / "subagents").glob("subagent_*.json"))
            self.assertEqual(1, len(traces))
            self.assertIn("rank_products", traces[0].read_text(encoding="utf-8"))

    def test_mock_mode_runs_complete_agent_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            agent = ShopkeeperAgent(workspace=tmp, mock_mode=True)
            result = agent.run("帮我找适合抖店卖的夏季连衣裙，挑5个靠谱的并铺货", auto_confirm=True)
            self.assertTrue(result.success)
            self.assertEqual(PlanState.DONE, result.state)
            self.assertIn("publish_dry_run", [task.tool_name for task in result.plan.tasks])
            traces = list((Path(tmp) / "subagents").glob("subagent_*.json"))
            self.assertGreaterEqual(len(traces), 4)

    def test_llm_planner_adapter_accepts_structured_plan(self):
        provider = JSONPlannerProvider(
            """
            {
              "name": "LLM plan",
              "tasks": [
                {"goal": "search", "tool_name": "search_products", "args": {"query": "连衣裙"}},
                {"goal": "rank", "tool_name": "rank_products", "depends_on": [0]}
              ]
            }
            """
        )
        plan = LLMPlanner(provider).create_plan("帮我找连衣裙")
        self.assertEqual("LLM plan", plan.name)
        self.assertEqual([plan.tasks[0].id], plan.tasks[1].parent_task_ids)


if __name__ == "__main__":
    unittest.main()
