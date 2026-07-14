# 1688 Shopkeeper Agent Design

这个分支把原来的 1688 Skill 改造成一个面试可讲的垂直电商 Agent。原项目的
`scripts/capabilities/*` 保持为业务工具层，新增 `agent/` 作为 Agent 编排层。

## 设计目标

- 证明它不是简单 ChatBot，而是可规划、可执行、可恢复的业务 Agent。
- Planner 只做任务拆解，不直接调用业务 API。
- Worker/SubAgent 只执行单个 Task，使用受限上下文和工具白名单。
- Plan 模式由有限状态机约束，模型或执行器不能随意跳状态。
- 每次计划变更都生成 checkpoint，便于失败恢复和目标漂移回滚。
- 长期记忆以 `MEMORY.md` 为唯一权威源，索引和图谱都是派生数据。

## 运行方式

只生成计划，不调用 1688 API：

```bash
python agent_cli.py plan "帮我找适合抖店卖的夏季连衣裙，挑5个靠谱的"
```

生成计划但等待确认：

```bash
python agent_cli.py run "帮我找适合抖店卖的夏季连衣裙，挑5个靠谱的"
```

自动确认并执行工具：

```bash
python agent_cli.py run "帮我找适合抖店卖的夏季连衣裙，挑5个靠谱的" --yes
```

无 AK 面试演示完整成功路径：

```bash
python agent_cli.py run "帮我找适合抖店卖的夏季连衣裙，挑5个靠谱的并铺货" --mock --yes
```

Web 页面演示：

```bash
python web_demo.py --host 127.0.0.1 --port 8765
```

打开 `http://127.0.0.1:8765`，页面会展示 Plan、推荐商品、SubAgent trace 和 raw JSON。

没有配置 AK 时，搜索任务会失败，状态机会进入 `updating`，不会继续执行依赖任务。

## 状态机

状态定义在 `agent/state.py`，流转逻辑在 `agent/fsm.py`：

```text
intent -> direct -> doing -> done/failed
       \-> init -> confirmed -> doing -> done/failed
                              \-> updating
```

含义：

- `intent`：判断 Direct 还是 Plan。
- `direct`：简单任务直接生成短计划并执行。
- `init`：Planner 创建任务 DAG。
- `confirmed`：等待人类确认，默认不执行业务工具。
- `doing`：Worker 执行 ready tasks。
- `updating`：工具失败或目标漂移后的重规划状态。
- `done` / `failed` / `rejected`：终态。

## 工具白名单

工具白名单在 `agent/tooling.py`：

- `intent` 只能用 `set_work_mode`。
- `init` 只能创建/查询计划和记忆，不能调用业务 API。
- `confirmed` 只能确认或询问人类。
- `doing` 不能直接调用业务 API，只能调用 `worker_spawn`。
- SubAgent/Worker 拿到独立的执行工具白名单：`search_products`、`rank_products`、`list_shops`、`publish_dry_run` 等。
- 真实写操作没有暴露给 Worker，只有 `publish_dry_run`。

这和 Kugelblitz 的重点一致：不同状态下模型看到的工具集合不同，降低幻觉调用和越权调用风险。

## SubAgent 上下文隔离

`agent/subagent.py` 中的 `SubAgentManager` 会在 `doing` 状态为每个 ready task 动态创建一个
短生命周期 SubAgent，并把 trace 写到：

```text
.agent_data/subagents/subagent_{id}.json
```

`agent/worker.py` 中的 `WorkerAgent` 每次只接收：

- 原始目标；
- 当前 task goal；
- 当前状态允许的工具；
- 从 `MEMORY.md` 检索到的少量记忆片段。

它默认不接收完整对话历史和完整计划，避免单个执行子任务污染全局上下文。

权限分层是：

```text
FSM doing state -> worker_spawn
SubAgent worker -> search_products / rank_products / list_shops / publish_dry_run
```

这比“主 Agent 直接调用所有工具”更接近生产级 Agent runtime。

SubAgent 内部是简化 ReAct loop，执行轨迹会记录到 trace 的 `steps` 字段：

```json
{
  "thought": "Use the task-specific tool with isolated context...",
  "tool_name": "search_products",
  "observation_success": true
}
```

当前 `_decide_next_action()` 是确定性决策，生产版可替换为 LLM，让 SubAgent 自主选择下一步工具。

## Planner 抽象

`agent/planner.py` 中提供两层 Planner：

- `HeuristicPlanner`：默认规则版，便于本地稳定演示；
- `LLMPlanner`：结构化 Planner 适配器，可接 OpenAI structured outputs、function calling 或公司内部模型网关。
- 设置 `AGENT_PLANNER=llm` 时会尝试使用 `agent/llm_provider.py` 中的 OpenAI-compatible provider；没配置 key 时 fallback 到规则版。

接口是：

```python
provider.generate_plan(goal) -> {
  "name": "...",
  "tasks": [
    {"goal": "...", "tool_name": "search_products", "args": {...}},
    {"goal": "...", "tool_name": "rank_products", "depends_on": [0]}
  ]
}
```

这让 Planner 专注“产生合法 DAG”，Runtime 专注“状态流转和权限控制”。

## Mock Mode 与 Evals

`agent/mock_shopkeeper_tools.py` 使用 workspace 下的 SQLite 数据库模拟业务数据源：

```text
.agent_data/mock_catalog.sqlite
```

其中包含 `products`、`shops`、`publish_runs` 三张表。这样 Mock 模式不是纯写死返回，
而是从本地商品库搜索、读取店铺，并记录 dry-run 铺货请求。Real API 模式仍然走 1688 远端接口。

测试覆盖在 `tests/test_agent_core.py`：

- Planner 生成 DAG；
- 状态工具白名单；
- checkpoint 落盘；
- `MEMORY.md` 权威源重载；
- 动态 SubAgent spawn trace；
- mock mode 完整 `search -> rank -> shops -> publish_dry_run -> done`；
- LLMPlanner 结构化计划适配。

## Observability

观测系统参考 Kugelblitz 的 Hook 风格：

```text
AgentEventHooks
  -> HookInstrument
  -> Observer
  -> JSONLObserver / LangfuseObserver
```

默认本地落盘：

```text
.agent_data/observability/trace_{id}.jsonl
```

接入 Langfuse：

```bash
set AGENT_OBSERVER=langfuse
set LANGFUSE_HOST=https://cloud.langfuse.com
set LANGFUSE_PUBLIC_KEY=...
set LANGFUSE_SECRET_KEY=...
```

配置后，`agent.run`、state transition、planner、subagent、task update、tool call、approval 等事件会通过
Langfuse ingestion API 上报。未配置 key 时自动 fallback 到 JSONLObserver。

## 写操作审批

普通“铺货”只会执行 `publish_dry_run`。当用户明确说“正式铺货/确认铺货”时，Plan 会追加：

```text
request_publish_approval
```

该任务只创建审批单，不直接执行真实写操作。审批文件位于：

```text
.agent_data/approvals/approval_{id}.json
```

审批通过后再执行：

```bash
python agent_cli.py approve approval_xxx --mock
```

`publish_real` 不在普通 Worker 工具白名单中，只能由 approval 路径调用。

## 恢复策略

当前内置基础恢复：

- 搜索为空：自动放宽关键词并重试一次；
- AK 未配置/签名无效：进入修复状态，不继续执行后续任务；
- 目标漂移：Reviewer 触发 checkpoint rollback 并进入 `updating`。

## 可解释推荐

`rank_products` 会为商品生成：

```text
ranking_score
reasons
```

原因包括销量高、好评率高、复购表现好、揽收率稳定、铺货竞争风险等。

## Checkpoint

`agent/persist.py` 中的 `AgentStore.save_plan()` 每次保存都会：

- 更新 `plan.json`；
- 追加 `plan.jsonl`；
- 写入 `plans/{plan_id}/checkpoints/{version}.json`。

目标漂移或失败时，状态机可以读取前一版 checkpoint 并进入 `updating`。

## 目标漂移检测

`agent/reviewer.py` 是独立 Reviewer。当前版本是确定性规则：

- 检查原始目标和最近执行轨迹的关键词重叠；
- 如果原目标属于 1688/电商域，而执行轨迹离开该领域，则判定漂移；
- 漂移后状态机回滚 checkpoint 并进入 `updating`。

生产版可以把 `Reviewer.review()` 替换成结构化 LLM function calling。

## 长期记忆

`agent/memory.py` 使用：

- `.agent_data/memory/MEMORY.md` 作为唯一权威源；
- 内存关键词索引从 `MEMORY.md` 重建；
- `memory_graph.jsonl` 作为知识图谱/实体关系的预留派生文件。

这对应主流 Agent 记忆设计：Markdown/文本是人类可审查的真源，向量库或图数据库只做检索增强。

## 面试讲法

这个项目可以这样描述：

> 我把一个 1688 电商 Skill 改造成了垂直领域 Agent。业务能力仍然是可测试的工具层；
> 新增 Agent 层负责意图路由、计划状态机、工具白名单、SubAgent 上下文隔离、
> checkpoint 恢复、目标漂移检测和长期记忆。写操作只暴露 dry-run，避免 Agent 越权。
