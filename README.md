# 1688 Agent Shopkeeper

面向 1688 选品、店铺查询和铺货预检查场景的垂直电商 Agent 项目。项目基于原 `1688-shopkeeper` Skill 的真实业务能力层，新增 Agent Runtime、Plan 模式状态机、SubAgent 上下文隔离、长期记忆、安全审批和 Hook 观测，用于展示 Agent 开发岗位所需的工程能力。

## Source

本项目基于开源项目 [next-1688/1688-shopkeeper](https://github.com/next-1688/1688-shopkeeper) 改造而来。原项目提供 1688 商品搜索、店铺查询、铺货等 Skill 能力；本项目在其业务能力层之上重构为垂直电商 Agent Runtime，重点补充 Plan 模式、SubAgent、记忆、安全审批和观测能力。

## Highlights

- Plan 模式状态机：支持 `intent/init/confirmed/doing/updating/done/failed/rejected` 流转、任务 checkpoint 和失败状态保存。
- Planner/Worker 分离：Planner 只负责规划，Worker 根据任务动态创建 SubAgent 执行。
- DAG 执行引擎：Plan 支持 `depends_on`，运行时会做拓扑调度、循环依赖检测和失败依赖阻断。
- SubAgent 上下文隔离：每个 SubAgent 只获得当前任务、局部上下文和角色工具白名单。
- 工具安全策略：按运行状态和 Worker 角色限制工具调用；正式铺货不进入普通 Worker，必须走 approval。
- 记忆系统：Working Memory 管理会话上下文，`MEMORY.md` 作为长期记忆权威源，Memory Pipeline 负责 extractor/dedup/conflict/compress/reflection，SQLite 和 graph JSONL 作为派生索引。
- Hook 观测：参考 Kugelblitz 风格，通过 Hook 捕获状态流转、checkpoint、工具调用和 SubAgent 事件，支持 JSONL 与 Langfuse。
- Mock/Real 双模式：Mock 模式使用本地 SQLite 商品库，Real 模式包装原 1688 Skill API 能力。

## Architecture

```text
agent/
├─ config/          # runtime/env settings
├─ core/            # Plan/Task state, FSM, hooks
├─ planning/        # planner and goal-drift detection
├─ runtime/         # runtime factory, worker, isolated subagent
│  └─ dag/          # task graph, scheduler, DAG executor
├─ tools/           # tool registry, schemas, policy, 1688 adapters
├─ memory/          # working memory, MEMORY.md store, pipeline, graph/index/reflection
├─ persist/         # plan store and checkpoints
├─ safety/          # approval workflow
├─ observability/   # hook instrument, JSONL, Langfuse
├─ providers/       # OpenAI-compatible planner provider
└─ ui/              # UI-facing adapters

scripts/            # legacy 1688 Skill API capability layer
docs/               # design docs and legacy Skill references
prompts/            # planner/memory/reviewer prompts
tests/              # core Agent tests
```

详细设计见 [AGENT_DESIGN.md](AGENT_DESIGN.md)。

## Quick Start

Mock 模式不需要 API Key，适合本地演示 Agent 流程：

```bash
python agent_cli.py run "帮我找适合抖店卖的夏季连衣裙，挑5个靠谱的并铺货" --mock --yes
```

启动用户端页面：

```bash
python web_demo.py
```

打开：

```text
http://127.0.0.1:8765
```

## CLI

生成计划但不执行：

```bash
python agent_cli.py plan "帮我找适合抖店卖的夏季连衣裙，挑5个靠谱的并铺货" --mock
```

自动确认并执行：

```bash
python agent_cli.py run "帮我找适合抖店卖的夏季连衣裙，挑5个靠谱的并铺货" --mock --yes --json
```

正式铺货会创建审批，而不是直接写入：

```bash
python agent_cli.py run "帮我正式铺货夏季连衣裙" --mock --yes --json
python agent_cli.py approve approval_xxx --mock
```

## Observability

默认观测输出到 `.agent_data*/observability/*.jsonl`。

接入 Langfuse：

```bash
set AGENT_OBSERVER=langfuse
set LANGFUSE_HOST=https://cloud.langfuse.com
set LANGFUSE_PUBLIC_KEY=your_public_key
set LANGFUSE_SECRET_KEY=your_secret_key
```

## Real 1688 Mode

`scripts/` 是原始 `1688-shopkeeper` 的真实业务能力层，包含 AK 配置、HTTP 请求、商品搜索、店铺查询、铺货等能力。Agent 的真实模式通过 `agent/tools/real_shopkeeper.py` 包装调用这些能力。

Real 模式需要先配置 1688/OpenClaw AK，Mock 模式不需要。

## Tests

```bash
python -m compileall agent agent_cli.py web_demo.py tests
python -m unittest discover -s tests -v
```

## Resume Bullets

- 设计垂直电商 Agent 的 Plan 模式状态机，将自然语言经营目标拆解为可 checkpoint 的任务流，并支持失败恢复和目标漂移检测。
- 构建 `MEMORY.md + SQLite` 长期记忆体系，以 Markdown 作为权威源、SQLite 作为派生索引，支持选品策略沉淀和检索增强。
- 实现 Planner/Worker/SubAgent 分层架构，通过动态 SubAgent 和工具白名单实现上下文隔离与越权调用防护。
- 参考 Kugelblitz Hook 风格实现 Agent 观测链路，统一捕获状态流转、工具调用、checkpoint 和 SubAgent 事件，并支持 Langfuse 上报。
