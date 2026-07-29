# 终端录屏脚本

建议录制 4–6 分钟，画面中不要展示 `.env` 或 API Key。

## 录制前

1. 在 `.env` 填写 `DEEPSEEK_API_KEY`。
2. 打开项目根目录终端。
3. 运行测试：

   ```powershell
   python -m unittest discover -s tests -v
   ```

4. 若此前演示过，使用新的 session 名，不需要删除旧数据。

## 镜头 1：真实 LLM + 多工具循环

```powershell
python -m mini_agent ask "计算 (123+456)*7，把结果加入待办，再列出待办" --session demo-main --show-trace
```

讲解点：

- 模型从 Schema 自主选择 calculator 与 todo；
- trace 展示参数和工具结果；
- 最终回答由工具结果生成。

## 镜头 2：带工具追问

```powershell
python -m mini_agent chat --session demo-main --show-trace
```

输入：

```text
刚才的计算结果是多少？把那个待办标记为完成
列出现在的待办
/exit
```

讲解点：相同 session 能恢复上下文，并可用 list 返回的 todo id 继续操作。

## 镜头 3：窗口隔离

```powershell
python -m mini_agent ask "记一个写周报的待办" --session demo-window-2
python -m mini_agent ask "列出待办" --session demo-window-2
python -m mini_agent ask "列出待办" --session demo-main
```

讲解点：两个窗口的待办互不影响。

## 镜头 4：持久化与 trace

```powershell
python -m mini_agent sessions
python -m mini_agent trace --session demo-main --limit 20
```

展示 `.agent_data/sessions/` 和 `.agent_data/traces/` 的文件名即可，不需要展开可能含有
用户输入的完整文件。

## 镜头 5：代码导航

快速打开：

- `mini_agent/runtime.py`：循环；
- `mini_agent/tools/base.py` 与 `registry.py`：工具协议和注册；
- `mini_agent/context.py`：压缩；
- `mini_agent/session_store.py`：session 隔离；
- `tests/test_runtime.py`：端到端离线测试。

最后展示 README 的功能对照表和 `docs/architecture-interview.md`。
