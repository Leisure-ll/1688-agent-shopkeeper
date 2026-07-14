# 1688 Agent Shopkeeper

面向 1688 选品铺货场景的垂直电商 Agent。项目保留原始 1688 Skill 能力，并在其上增加 Plan 模式、SubAgent 隔离执行、长期记忆、安全审批和 Hook 观测。

## Core Flow

1. 用户输入自然语言目标，例如“帮我找适合抖店卖的夏季连衣裙，挑 5 个靠谱的并铺货”。
2. Intent classifier 先判断目标是 simple / complex / risky，并选择 shop lookup、product search、selection publish 等路线。
3. Planner 根据 intent route 生成不同规模的任务计划，输出可校验任务列表。
4. PlanModeFSM 驱动 `intent/init/confirmed/doing/updating/done/failed/rejected` 状态流转，并在关键节点写 checkpoint。
5. DAG executor 根据任务依赖做拓扑调度，检测循环依赖，并在失败时阻断下游任务。
6. 如果任务失败，FSM 进入 `updating`，PlanAdaptor 可重置失败任务并等待确认或自动恢复。
7. Worker 按任务动态创建 SubAgent，SubAgent 只拿到当前任务上下文和角色工具白名单。
8. 写操作默认只做 dry-run；正式铺货必须先创建 approval，再通过 `approve` 命令执行。
9. Hooks 捕获状态流转、计划生成、checkpoint、SubAgent、工具调用等事件，并导出到 JSONL 或 Langfuse。

## Interview Highlights

- Plan 模式状态机：任务 DAG、checkpoint、失败恢复、目标漂移检测。
- Checkpoint 恢复：支持 checkpoint list、replay、diff 和 resume。
- Adapt 状态：任务失败后进入 `updating`，支持失败任务重置和二次确认执行。
- Intent 路由：`intent` 状态调用 `classify_intent` 区分 simple/complex/risky，并影响任务计划规模。
- DAG 执行引擎：支持 `depends_on`、拓扑调度、循环依赖检测和失败依赖阻断。
- 上下文隔离：主 Agent 规划调度，SubAgent 执行单任务，不共享完整全局上下文。
- 工具白名单：按状态和 Worker 角色限制工具访问，`publish_real` 不进入普通 Worker。
- 记忆系统：Working Memory 管理会话上下文，`MEMORY.md` 是长期记忆权威源，Memory Pipeline 负责 extractor/dedup/conflict/compress/reflection，SQLite 和 graph JSONL 只是派生索引。
- 观测系统：参考 Kugelblitz Hook 风格，runtime 只发事件，observer 负责落盘或上报 Langfuse。
- Session/Workspace：参考 Kugelblitz 的 workspace/session_context，把 plan、memory、trace、approval 归入统一会话边界，核心事件携带 `session_id`。
- Prompt Registry：prompt 文件有版本号，planner 调用可记录 prompt version。
- Provider Layer：支持 OpenAI-compatible / DeepSeek provider、timeout、retry 和 mock provider。
- Tool Audit：工具调用记录 role、risk、task、error，和 Hook trace 形成互补。
- MCP Adapter：以 MCP 风格暴露 tools/resources/prompts 描述，方便后续接入外部 Agent 客户端。

## Structure

```text
agent/
├─ config/          # runtime/env settings
├─ core/            # Plan/Task state, FSM, hooks
├─ planning/        # planner and goal-drift detection
├─ runtime/         # runtime factory, worker, isolated subagent
│  └─ dag/          # task graph, scheduler, DAG executor
├─ prompts/         # prompt registry and versioning
├─ tools/           # tool registry, schemas, policy, 1688 adapters
├─ memory/          # working memory, MEMORY.md store, pipeline, graph/index/reflection
├─ mcp/             # MCP-style tools/resources/prompts adapters
├─ persist/         # plan store and checkpoints
├─ safety/          # approval workflow
├─ observability/   # hook instrument, JSONL, Langfuse, tool audit
├─ providers/       # OpenAI-compatible/DeepSeek/mock providers and retry
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
