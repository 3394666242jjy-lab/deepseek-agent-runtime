import unittest

from mini_agent.context import ContextManager
from mini_agent.types import Session


class ContextManagerTests(unittest.TestCase):
    def test_compacts_old_messages_and_keeps_recent_verbatim(self):
        session = Session(
            session_id="s",
            messages=[
                {"role": "user" if index % 2 == 0 else "assistant", "content": f"message-{index}"}
                for index in range(12)
            ],
        )
        manager = ContextManager(max_messages=6, max_chars=10_000)
        self.assertTrue(manager.compact(session))
        self.assertIn("message-0", session.summary)
        self.assertEqual(session.messages[-1]["content"], "message-11")
        self.assertLessEqual(len(session.messages), 6)

    def test_summary_is_inserted_before_recent_history(self):
        session = Session(
            session_id="s",
            summary="用户喜欢简洁回答",
            messages=[{"role": "user", "content": "继续"}],
        )
        messages = ContextManager().build_messages("system", session)
        self.assertEqual(messages[0]["role"], "system")
        self.assertIn("用户喜欢简洁回答", messages[1]["content"])
        self.assertEqual(messages[2]["content"], "继续")


if __name__ == "__main__":
    unittest.main()
