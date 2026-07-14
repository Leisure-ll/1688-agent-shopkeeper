import os
from dataclasses import dataclass
from typing import Any

from agent.config.settings import AgentSettings
from agent.core.hooks import chain
from agent.memory.retriever import MemoryRetriever
from agent.memory.store import MemoryStore
from agent.memory.writer import MemoryWriter
from agent.observability.instrument import HookInstrument
from agent.observability.langfuse import LangfuseObserver
from agent.observability.observer import JSONLObserver
from agent.persist.plan_store import PlanStore
from agent.planning.intent import IntentClassifier
from agent.runtime.worker import AgentWorker
from agent.runtime.session import SessionStore
from agent.runtime.workspace import AgentWorkspace
from agent.safety.approval import ApprovalStore
from agent.tools.mock_shopkeeper import MockShopkeeperTools
from agent.tools.real_shopkeeper import RealShopkeeperTools
from agent.tools.registry import ToolRegistry


@dataclass
class AgentRuntime:
    settings: AgentSettings
    memory: MemoryStore
    approvals: ApprovalStore
    shopkeeper: Any
    registry: ToolRegistry
    hooks: Any
    store: PlanStore
    worker: AgentWorker
    workspace: AgentWorkspace
    sessions: SessionStore


def make_observer(settings: AgentSettings):
    if settings.observer == "langfuse" or os.environ.get("AGENT_OBSERVER") == "langfuse":
        try:
            return LangfuseObserver()
        except Exception:
            return JSONLObserver(settings.workspace)
    return JSONLObserver(settings.workspace)


def create_runtime(settings: AgentSettings) -> AgentRuntime:
    workspace = AgentWorkspace(settings.workspace)
    workspace.ensure()
    memory = MemoryStore(settings.workspace)
    writer = MemoryWriter(memory)
    retriever = MemoryRetriever(memory)
    approvals = ApprovalStore(settings.workspace)
    shopkeeper = MockShopkeeperTools(settings.workspace) if settings.mock else RealShopkeeperTools()
    intent_classifier = IntentClassifier()
    registry = ToolRegistry()
    registry.register("classify_intent", lambda goal: intent_classifier.classify(goal))
    registry.register("search_products", shopkeeper.search_products)
    registry.register("list_shops", shopkeeper.list_shops)
    registry.register("publish_dry_run", shopkeeper.publish_dry_run)
    registry.register("write_memory", writer.write)
    registry.register("memory_search", lambda query, limit=5: {"memories": retriever.retrieve(query, limit)})
    registry.register("request_publish_approval", approvals.request_publish)
    hooks = chain(HookInstrument(make_observer(settings)))
    worker = AgentWorker(registry, settings.workspace, hooks)
    sessions = SessionStore(workspace)
    return AgentRuntime(settings, memory, approvals, shopkeeper, registry, hooks, PlanStore(settings.workspace), worker, workspace, sessions)
