# AI Prompt 与问题解决记录

本文记录开发者如何使用 AI 完成本项目，以及项目开发过程中通过哪些 Prompt 发现并解决问题。
项目内部给 DeepSeek 使用的 System Prompt 放在最后，二者不应混淆：

- **开发 Prompt**：开发者向 AI 提出的项目需求和修改要求；
- **Runtime Prompt**：程序运行时发送给 DeepSeek、用于控制 Agent 行为的提示词。

## 1. 初始项目开发 Prompt

开发者向 AI 提供的核心任务如下：

```text
请按要求从零实现一个最小可用 Agent。

要求：
1. 不能依赖 LangGraph、OpenHands、OpenClaw 等现有 Agent 框架完成主流程，
   核心 Agent Runtime 需要自行实现。

2. 实现基本 Agent Loop：
   - 接收用户输入；
   - 判断直接回复还是调用工具；
   - 执行工具；
   - 根据工具结果决定继续循环还是返回最终答案。

3. 至少实现三个工具，例如：
   - calculator；
   - search（可以 Mock）；
   - read_docs、todo、weather 等自定义工具。

4. 实现工具注册机制。每个工具必须包含：
   - 名称；
   - 描述；
   - 参数 Schema。
   LLM 应根据 Schema 自主决定调用哪个工具。

5. 实现模型输出解析：
   - 提取最终回答；
   - 提取工具调用；
   - 兼容模型可能返回的思考或结构化内容。

6. 实现 Session 管理：
   - 不同窗口使用独立 Session；
   - Session 可以保存并恢复；
   - 不同窗口之间不能互相影响。

7. 实现 Context 管理：
   - 最大循环次数；
   - 支持持续对话和追问；
   - 支持带工具的追问；
   - Context 过长时进行基础压缩。

8. 增加基本异常处理和工具执行 Trace。

9. 构建测试用例测试上述功能。

10. 使用真实 DeepSeek LLM API。创建好 .env，我会填写 API Key。

提交内容：
- 完整代码；
- README，包括运行方式、系统设计、Memory 召回时机与放置方式；
- AI Prompt 与问题解决记录；
- 终端或网页操作录屏说明；
- 架构设计题答案。
```

这个 Prompt 决定了项目的主要边界：核心循环必须自己实现、真实模型负责工具决策、
工具执行由程序控制，同时需要补齐 Session、Context、Trace、测试和文档。

## 2. AI 对初始 Prompt 的任务拆解

AI 将任务拆成以下模块：

```text
DeepSeek API Client
        ↓
Model Output Parser
        ↓
Agent Runtime Loop
        ↓
Tool Registry + JSON Schema
        ↓
Session Store + Context Manager
        ↓
Trace + Error Boundary
        ↓
CLI + Tests + Documentation
```

实现时先定义统一的 `ModelDecision`，把模型响应转换成“最终回答或工具调用”，再实现循环：

```text
build context
→ call LLM
→ parse decision
→ validate and execute tools
→ append tool results
→ repeat or return
```

这样可以避免 DeepSeek HTTP 返回结构、工具逻辑和 Session 管理互相耦合。

## 3. 后续迭代 Prompt 与解决结果

### 3.1 整理为 GitHub 仓库

开发者 Prompt：

```text
帮我把项目改整洁一点，不要压缩包，我要上传 GitHub。
```

解决结果：

- 删除 ZIP、QA 副本和缓存文件；
- 将说明材料统一移动到 `docs/`；
- 添加 `.gitignore`、`.gitattributes`、`.editorconfig`；
- 添加 MIT License；
- 添加 GitHub Actions；
- 初始化 `main` 分支并创建提交；
- 检查暂存文件中没有 `.env` 和 API Key。

### 3.2 增加持续交互终端

开发者 Prompt：

```text
能不能改成用 py 启动后在终端一直等我输入，回答完以后继续等待输入？
```

解决结果：

- 增加根目录 `main.py`；
- 使用 `python main.py` 启动持续会话；
- 增加 `/help`、`/trace`、`/new`、`/exit`；
- 单轮 API 调用失败后不退出整个程序；
- 支持通过 `--session` 恢复指定会话。

### 3.3 API Key 修改后仍使用旧值

开发者 Prompt：

```text
检查代码是不是错了，为什么更换 API Key 后还是显示旧 Key 的 401 错误？
```

问题原因：

```python
os.environ.setdefault(key, value)
```

这段代码不会覆盖终端进程中已有的旧环境变量，因此即使 `.env` 已更新，程序仍可能
继续使用旧 Key。

解决结果：

- 显式指定的项目 `.env` 改为优先；
- 增加配置优先级测试；
- 检查 `.env` 中 Key 必须独立成行，不能放在 `#` 注释后；
- 日志和诊断过程不输出完整 Key。

### 3.4 简单计算返回大量旧内容

开发者 Prompt：

```text
我只计算一个 6×7，为什么返回之前的待办、计算和大量总结？
```

问题原因：

- `main.py` 默认重复使用名为 `default` 的 Session；
- 旧 Session 中包含之前的待办和工具结果；
- 模型把历史误认为本轮需要汇总的内容。

解决结果：

- `python main.py` 每次默认创建新的空白 Session；
- 只有显式指定 `--session` 才恢复旧会话；
- 增加 `/new` 命令；
- Runtime Prompt 增加“只回答当前问题”的规则；
- 简单问题默认返回简短纯文本。

### 3.5 测试发现导入失败

问题：

```text
python -m unittest discover -s tests
```

在 discovery 模式下，相对导入没有稳定的 package 上下文。

解决结果：

```python
from tests.fakes import FakeLLM
```

替换原来的相对导入，随后测试恢复通过。

### 3.6 工具成功但后续模型请求失败

问题：

```text
todo 工具已经执行成功，但如果下一次 LLM 请求失败，副作用可能没有保存。
```

解决结果：

- 每个工具执行后立即保存 Session；
- 不等到最终回答后才保存；
- 提高进程异常退出时的状态恢复能力。

### 3.7 最大循环次数到达后没有用户答案

问题：

```text
如果最后一步仍然是工具调用，达到最大循环次数后直接报错会浪费已有工具结果。
```

解决结果：

- 达到最大工具循环后，再执行一次不提供工具的模型调用；
- 要求模型只能根据已有结果生成最终回答；
- 如果最终调用也失败，再返回可查看 Trace 的降级提示。

## 4. 测试和验证方式

默认测试使用队列式 Fake LLM，不调用真实 DeepSeek：

- 不需要 API Key；
- 不消耗模型费用；
- 不受网络和模型随机性影响；
- 可以精确控制“先调用工具、再返回答案”的过程。

测试覆盖：

- 原生 Function Calling；
- JSON 降级协议；
- 非法工具参数；
- Calculator 注入攻击和除零；
- `read_docs` 路径穿越；
- 工具循环；
- 未知工具异常；
- Session 隔离和恢复；
- Context 压缩；
- 最大循环次数；
- Trace 生命周期；
- `.env` 配置优先级；
- 自动创建新 Session。

真实 DeepSeek API 不进入默认 CI，只在录屏前执行 Smoke Test。

## 5. AI 辅助范围

AI 主要用于：

- 需求拆解；
- 架构和风险分析；
- 代码草拟；
- 测试设计；
- README 和架构题整理；
- 根据运行截图定位问题；
- GitHub 仓库整理。

项目最终通过代码测试和实际终端运行验证，而不是只接受 AI 生成结果。核心 Runtime
没有使用第三方 Agent 框架，模型也不能绕过工具注册、参数校验和执行边界。

## 6. 附录：Runtime System Prompt

下面是程序运行时发送给 DeepSeek 的 Prompt。它不是“开发者要求 AI 完成项目”的 Prompt，
而是项目自身的一部分：

```text
你是一个可靠的中文 Agent。

你可以直接回答，也可以依据已提供的工具 Schema 自主调用一个或多个工具。

需要外部事实、计算、文档内容或待办操作时调用工具，不要编造工具结果。
只使用已注册工具和 Schema 中声明的参数。
工具失败时，能修正参数则重试，否则向用户说明。
收到工具结果后，判断继续调用工具还是返回最终答案。
不同 Session 的状态必须隔离。
只回答当前问题，不主动汇总无关历史。
简单问题使用适合终端阅读的简短纯文本回答。
```

参数校验、最大轮次、Session 隔离、文件安全和异常处理仍由代码强制实现，不能仅依赖
Prompt 保证。
