# 架构设计题

每个模块选择一题。重点写决策、失败模式和验证方法，而不是堆概念。

## 模块一：Context / Performance

### 选题 2：session 连续聊 200 轮，context 快爆了，如何压缩并保持流畅？

我不会把“200 轮”当固定触发器，而是维护 token budget，并在约 70% 时后台准备压缩、
85% 时强制切换。context 分四层：

1. **不可丢的控制层**：system/developer 规则、用户当前目标、权限、安全约束；
2. **working set**：最近若干轮原文、正在执行的计划、未解决问题、最近工具结果；
3. **结构化 episode summary**：人物/实体、用户偏好、已做决策、承诺、未完成项、
   失败尝试、关键产物引用；
4. **原始事件库**：完整消息和大工具输出不再常驻 prompt，但可按需回放。

压缩不是“把旧对话写成一段散文”。我会用固定 Schema 做增量合并：

```json
{
  "goal": "...",
  "facts": [{"value": "...", "source_event_id": "..."}],
  "decisions": [{"decision": "...", "reason": "..."}],
  "open_loops": [{"item": "...", "owner": "...", "status": "..."}],
  "user_preferences": [],
  "artifact_refs": []
}
```

每次只压缩上一份 summary 与新淘汰的事件，成本近似常量。大工具结果存对象存储，
prompt 只留 `artifact_id + 结论 + 可重取范围`。数字、日期、专有名词、否定结论和
未完成任务属于“锚点”，不能只靠自由文本摘要。

流畅性的关键不只是摘要质量，而是**可再水合**。新问题到来后，先用当前问题、
working set 和 open loops 检索原始事件；若命中旧决策或用户说“你之前提过”，把
最相关的 2–5 个原文片段放回 context，并附来源。摘要冲突时以更新的原文事件为准。

我会用三类指标验收：

- 连续性：代词指代、未完成任务续接、用户偏好保持率；
- 正确性：关键事实保留率、摘要矛盾率、错误旧记忆召回率；
- 成本：输入 token、首 token 延迟、压缩调用成本。

上线先做 shadow compaction：旧策略回答，新策略只记录预测，跑多轮回放集比较。
失败时宁可临时多带几段原文，也不要让一份不可信摘要成为单一事实源。

## 模块二：Memory

### 选题 1：半个月后用户问了以前问过的问题，如何召回？

“问过”不等于应该复用旧答案：世界事实可能变化，用户也可能想重新讨论。
我会先做一次低成本 query classification：

- 是稳定偏好/个人事实，还是时效性外部事实？
- 是明确回指（“上次那个”），还是语义相似？
- 旧答案可直接复用、需要刷新，还是只适合作为上下文？

memory 按 scope 隔离：当前 session、该用户跨 session、团队共享；默认只查前两层。
候选检索用 hybrid retrieval：关键词/BM25 保住专有名词与数字，向量召回语义相似，
再用时间衰减、重要性、明确保存标记和来源可信度重排。每条 memory 必须带
`source_event_id`、写入时间、类型、置信度、TTL/有效期，而不是只有一段 embedding。

召回策略：

1. 明确回指时阈值降低，优先原会话原文；
2. 用户偏好、长期项目约束可以高权重注入；
3. 天气、价格、版本等易变事实只提示“用户之前问过”，答案必须重新查询；
4. 候选相互冲突时优先新来源，并在必要时向用户确认；
5. 无高置信候选就不注入，避免“熟人幻觉”。

注入位置是单独的 `<retrieved_memory>` 区块，最多几条，包含来源时间和用途说明，
不能冒充 system instruction。敏感 memory 需要用户授权、可查看/删除、支持“不记住”。

评估不只看 Recall@K，还看“错误记忆造成的答案劣化”：precision、冲突解决准确率、
时效性刷新率、隐私 scope 泄漏率，以及有/无 memory 的成对回答胜率。

## 模块三：Task

### 选题 2：每天早上 9 点根据昨天聊天做复盘总结，如何设计？

我会把它设计成持久化定时任务，而不是让一个对话进程睡到 9 点：

```text
Scheduler → create job_run → snapshot yesterday events → summarize
          → validate → save artifact → notify → mark completed
```

创建任务时保存 `user_id`、时区、cron、数据范围、通知渠道、授权范围和 prompt 版本。
“昨天”按用户本地时区的 `[00:00, 24:00)` 计算。9 点触发后先创建带唯一键
`(task_id, local_date)` 的 `job_run`，天然幂等；然后读取一个固定 high-water mark
之前的消息快照，防止运行中新增消息让结果漂移。

总结分两阶段：并行生成各 session 的结构化摘要，再聚合成“进展、决策、风险、
未完成项、今日建议”。工具输出只取摘要和引用，不把大文件全文灌进模型。最终结果
经过 Schema 校验和安全过滤后存为 artifact，通知消息只放摘要和链接。

失败采用指数退避和 dead-letter queue；9 点系统宕机恢复后执行一次 catch-up，
但同一天不会重复发送。通知发送与任务完成用 outbox pattern，避免“数据库成功但
消息没发”或反过来。用户修改时区后只影响下一周期，历史 run 保留原时区快照。

用户必须能暂停、立即运行、补跑某天、修改范围和彻底删除。监控指标包括准点率、
完成率、重复发送率、输入覆盖率、每次成本和用户点击/纠错率。

## 模块四：Tool / Session Runtime

### 选题 2：session busy 时新用户消息或异步工具完成事件到达，如何处理？

核心原则是**同一 session 单写者，外部执行可并行**。每个 session 对应一个 actor
或带 fencing token 的 lease；所有输入统一转成有序事件：

```text
UserMessage | ToolCompleted | ToolFailed | Cancel | Timeout
```

事件先写 durable inbox 再确认接收，字段包含 `event_id`、`session_id`、序号、
因果 `run_id/tool_call_id` 和幂等键。actor 每次只推进一个状态机：

`idle → reasoning → waiting_tool → reasoning → completed/cancelled`。

busy 时用户新消息不能一刀切。我会按意图分三类：

- “停止/改目标”是高优先级 control event：取消当前 generation，给未完成工具发
  best-effort cancel，并提升 session generation/version；
- 补充材料进入当前 run 的 pending input，在下一个安全点合并；
- 独立新请求排队，并立即回执“已收到，当前任务结束后处理”。

异步 `ToolCompleted` 必须携带原 `run_id + tool_call_id + generation`。如果仍是当前
等待项，就写入结果并唤醒 actor；如果 run 已取消或 generation 过期，结果存为
orphan artifact 供审计，但不能直接污染当前 prompt。重复完成事件由幂等键去重。

竞态通过乐观版本号解决：状态更新使用 CAS；lease 过期后旧 worker 即使回来，
也因 fencing token 较旧无法提交。工具回调只写事件，不能直接改 session state。

对用户体验，长工具启动后立即返回 `run_id` 和进度；可展示队列位置、取消和最终通知。
关键测试是模型化并发测试：消息/完成/取消的不同排列必须收敛到同一合法状态，
并验证不丢事件、不重复副作用、不把旧工具结果注入新任务。

## 模块五：Agent Runtime 架构对比

### 选题 1：Claude Code 工具输出与 OpenAI-compatible function calling 的不同

先区分“Claude Code 产品 Runtime”和“模型 API 协议”。Claude/Anthropic 消息内容
天然是异构 block 数组：assistant 产生 `tool_use` block（`id/name/input`），客户端
随后在 **user role** 消息里回传 `tool_result` block，并用 `tool_use_id` 关联。
同一条消息可组合 text、image、tool_use、tool_result。参考
[Anthropic Tool Use](https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/implement-tool-use)。

常见 OpenAI-compatible Chat Completions（GLM、豆包等通常兼容这一形态）是：
assistant message 顶层有 `tool_calls[]`，参数常为 JSON 字符串；执行后用独立的
`role: "tool"` message 与 `tool_call_id` 回传。DeepSeek 的
[Tool Calls](https://api-docs.deepseek.com/guides/tool_calls) 也是这个范式。
需要注意，不同国内服务只是“兼容”，对并行调用、strict schema、流式参数、
空 content、错误字段的细节支持可能不同，Runtime 不能假设完全一致。

Anthropic block 模型的优点：

- 文本、图片、工具请求/结果统一为可组合内容，适合 coding agent 的多模态轨迹；
- `tool_result` 可显式标记错误，也能承载多个内容 block；
- 一条 turn 内多个 block 的顺序语义清楚。

代价是协议更严格：`tool_result` 必须紧跟对应 `tool_use`，role 看起来像 user，
通用 message store 和中间件需要理解 block，而不能只按纯文本处理。

OpenAI-compatible 的优点：

- 工具请求与 `tool` role 清晰，生态、网关和 SDK 覆盖广；
- 扁平消息便于日志、数据库和多供应商适配；
- 上手成本低，现有业务函数容易暴露为 JSON Schema。

代价是“兼容层”容易掩盖差异：arguments 可能是增量字符串，Schema strict 能力不同，
多工具顺序和错误表达不统一；文本/图片/工具结果的组合能力通常不如 block 模型自然。

我的 Runtime 内部不会直接绑定任一 wire format，而是归一化为：

```text
ModelDecision(content, tool_calls[])
ToolCall(id, name, typed_arguments)
ToolResult(ok, data, error, metadata)
```

provider adapter 负责 Anthropic block 或 OpenAI-compatible message 的双向转换；
session/event store 只保存统一事件。这样切模型不会迫使工具执行层和调度状态机重写。
