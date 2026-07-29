import tempfile
import unittest
from pathlib import Path

from mini_agent.tools.base import ToolError
from mini_agent.tools.builtin import build_default_registry
from mini_agent.types import Session


class ToolRegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.docs = Path(self.temp.name)
        (self.docs / "note.md").write_text("hello docs", encoding="utf-8")
        self.registry = build_default_registry(self.docs)
        self.context = {"session": Session(session_id="s")}

    def tearDown(self):
        self.temp.cleanup()

    def test_has_at_least_three_schema_described_tools(self):
        schemas = self.registry.schemas()
        self.assertGreaterEqual(len(schemas), 3)
        for schema in schemas:
            function = schema["function"]
            self.assertTrue(function["name"])
            self.assertTrue(function["description"])
            self.assertEqual(function["parameters"]["type"], "object")

    def test_todo_is_session_scoped_state(self):
        result = self.registry.execute(
            "todo", {"action": "add", "text": "写周报"}, self.context
        )
        self.assertTrue(result.ok)
        listed = self.registry.execute("todo", {"action": "list"}, self.context)
        self.assertEqual(listed.data["todos"][0]["text"], "写周报")

    def test_schema_validation_rejects_missing_required(self):
        with self.assertRaisesRegex(ToolError, "缺少必填参数"):
            self.registry.execute("calculator", {}, self.context)

    def test_read_docs_prevents_path_traversal(self):
        with self.assertRaisesRegex(ToolError, "只允许读取"):
            self.registry.execute(
                "read_docs", {"path": "../secret.txt"}, self.context
            )


if __name__ == "__main__":
    unittest.main()
