# 1688 Agent Shopkeeper

面向 1688 选品铺货场景的垂直电商 Agent。项目保留原始 1688 Skill 能力，并在其上增加 Plan 模式、SubAgent 隔离执行、长期记忆、安全审批和 Hook 观测。

## Core Flow

1. 用户输入自然语言目标，例如“帮我找适合抖店卖的夏季连衣裙，挑 5 个靠谱的并铺货”。
2. Planner 只负责生成任务计划，输出可校验任务列表。
3. PlanModeFSM 驱动 `intent/init/confirmed/doing/updating/done/failed/rejected` 状态流转，并在关键节点写 checkpoint。
4. Worker 按任务动态创建 SubAgent，SubAgent 只拿到当前任务上下文和角色工具白名单。
5. 写操作默认只做 dry-run；正式铺货必须先创建 approval，再通过 `approve` 命令执行。
6. Hooks 捕获状态流转、计划生成、checkpoint、SubAgent、工具调用等事件，并导出到 JSONL 或 Langfuse。

## Interview Highlights

- Plan 模式状态机：任务 DAG、checkpoint、失败恢复、目标漂移检测。
- 上下文隔离：主 Agent 规划调度，SubAgent 执行单任务，不共享完整全局上下文。
- 工具白名单：按状态和 Worker 角色限制工具访问，`publish_real` 不进入普通 Worker。
- 长期记忆：`MEMORY.md` 是唯一权威源，SQLite 只是派生检索索引。
- 观测系统：参考 Kugelblitz Hook 风格，runtime 只发事件，observer 负责落盘或上报 Langfuse。

## Structure

```text
agent/
├─ config/          # runtime/env settings
├─ core/            # Plan/Task state, FSM, hooks
├─ planning/        # planner and goal-drift detection
├─ runtime/         # runtime factory, worker, isolated subagent
├─ tools/           # tool registry, schemas, policy, 1688 adapters
├─ memory/          # MEMORY.md store, retriever, writer, graph events
├─ persist/         # plan store and checkpoints
├─ safety/          # approval workflow
├─ observability/   # hook instrument, JSONL, Langfuse
├─ providers/       # OpenAI-compatible planner provider
└─ ui/              # UI-facing adapters
```

`scripts/` 是原 1688-shopkeeper Skill 的真实 API 能力层，真实模式通过 `agent/tools/real_shopkeeper.py` 包装调用它。`docs/legacy_skill_references/` 是原 Claw Skill 文档，运行时不依赖，只作为业务背景资料保留。

## Run

```bash
python agent_cli.py run "帮我找适合抖店卖的夏季连衣裙，挑5个靠谱的并铺货" --mock --yes
python web_demo.py
```

Web demo: `http://127.0.0.1:8765`

Langfuse:

```bash
set AGENT_OBSERVER=langfuse
set LANGFUSE_HOST=https://cloud.langfuse.com
set LANGFUSE_PUBLIC_KEY=...
set LANGFUSE_SECRET_KEY=...
```
