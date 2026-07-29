import json
import tempfile
import unittest
from pathlib import Path

from mini_agent.config import Settings
from mini_agent.runtime import AgentRuntime
from mini_agent.tools.builtin import build_default_registry
from mini_agent.types import ModelDecision, ToolCall

from tests.fakes import FakeLLM


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.settings = Settings(
            api_key="test",
            data_dir=self.root / "data",
            max_steps=4,
            context_max_messages=12,
            context_max_chars=20_000,
        )
        self.docs = self.root / "docs"
        self.docs.mkdir()
        (self.docs / "knowledge.md").write_text("runtime knowledge", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def runtime(self, decisions):
        fake = FakeLLM(decisions)
        runtime = AgentRuntime(
            self.settings,
            llm=fake,
            tools=build_default_registry(self.docs),
        )
        return runtime, fake

    def test_tool_loop_then_final_answer(self):
        runtime, fake = self.runtime(
            [
                ModelDecision(
                    tool_calls=[
                        ToolCall(
                            id="call_calc",
                            name="calculator",
                            arguments={"expression": "6*7"},
                        )
                    ]
                ),
                ModelDecision(content="计算结果是 42。"),
            ]
        )
        result = runtime.run("window-1", "6乘7是多少？")
        self.assertEqual(result.answer, "计算结果是 42。")
        self.assertEqual(result.steps, 2)
        self.assertEqual(result.tool_calls[0]["result"]["data"]["result"], 42)
        tool_message = fake.calls[1]["messages"][-1]
        self.assertEqual(tool_message["role"], "tool")
        self.assertIn('"result": 42', tool_message["content"])

    def test_unknown_tool_becomes_observable_error_and_loop_continues(self):
        runtime, _ = self.runtime(
            [
                ModelDecision(
                    tool_calls=[
                        ToolCall(id="bad", name="not_registered", arguments={})
                    ]
                ),
                ModelDecision(content="该工具不可用。"),
            ]
        )
        result = runtime.run("s", "调用不存在的工具")
        self.assertFalse(result.tool_calls[0]["result"]["ok"])
        self.assertIn("未知工具", result.tool_calls[0]["result"]["error"])

    def test_sessions_isolate_todos_and_can_resume(self):
        runtime_a, _ = self.runtime(
            [
                ModelDecision(
                    tool_calls=[
                        ToolCall(
                            id="a1",
                            name="todo",
                            arguments={"action": "add", "text": "查天气"},
                        )
                    ]
                ),
                ModelDecision(content="已记录。"),
            ]
        )
        runtime_a.run("window-1", "记一个待办")
        session_a = runtime_a.sessions.load("window-1")
        session_b = runtime_a.sessions.load("window-2")
        self.assertEqual(session_a.state["todos"][0]["text"], "查天气")
        self.assertNotIn("todos", session_b.state)

        resumed, _ = self.runtime([ModelDecision(content="欢迎回来。")])
        result = resumed.run("window-1", "继续")
        self.assertEqual(result.answer, "欢迎回来。")
        self.assertGreaterEqual(len(resumed.sessions.load("window-1").messages), 4)

    def test_trace_contains_tool_lifecycle(self):
        runtime, _ = self.runtime(
            [
                ModelDecision(
                    tool_calls=[
                        ToolCall(
                            id="c1",
                            name="calculator",
                            arguments={"expression": "1+1"},
                        )
                    ]
                ),
                ModelDecision(content="2"),
            ]
        )
        runtime.run("trace-test", "算一下")
        events = [item["event"] for item in runtime.traces.read("trace-test")]
        self.assertIn("tool_started", events)
        self.assertIn("tool_finished", events)
        self.assertIn("run_finished", events)
        path = self.settings.data_dir / "traces" / "trace-test.jsonl"
        for line in path.read_text(encoding="utf-8").splitlines():
            json.loads(line)

    def test_max_steps_forces_tool_free_synthesis(self):
        settings = Settings(
            api_key="test",
            data_dir=self.root / "max-data",
            max_steps=1,
            context_max_messages=12,
            context_max_chars=20_000,
        )
        fake = FakeLLM(
            [
                ModelDecision(
                    tool_calls=[
                        ToolCall(
                            id="c1",
                            name="calculator",
                            arguments={"expression": "2+2"},
                        )
                    ]
                ),
                ModelDecision(content="根据已有结果，答案是 4。"),
            ]
        )
        runtime = AgentRuntime(
            settings,
            llm=fake,
            tools=build_default_registry(self.docs),
        )
        result = runtime.run("bounded", "计算 2+2")
        self.assertEqual(result.steps, 1)
        self.assertEqual(result.answer, "根据已有结果，答案是 4。")
        self.assertEqual(fake.calls[-1]["tools"], [])


if __name__ == "__main__":
    unittest.main()
