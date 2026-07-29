# 演示知识库

## Agent Runtime

本项目的核心循环为：

1. 接收用户输入并写入指定 session。
2. 组装 system prompt、历史摘要和最近消息。
3. 把工具名称、描述及 JSON Schema 发给 DeepSeek。
4. 解析直接回答、原生 function calling 或 JSON 降级协议。
5. 校验工具参数，执行工具，将结果作为 `tool` 消息写回上下文。
6. 信息不足时继续循环，足够时返回最终答案。

## Session 与 Context

每个窗口使用不同 `session_id`。消息、摘要、待办和 trace 都在该命名空间中，
不会被其他窗口读取。超过消息数或字符阈值后，较早内容会压缩为摘要，最近消息保留原文。
