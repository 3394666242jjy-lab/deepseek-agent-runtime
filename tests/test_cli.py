import re
import unittest

from mini_agent.cli import new_session_id


class CliTests(unittest.TestCase):
    def test_new_session_id_is_safe_and_readable(self):
        session_id = new_session_id()
        self.assertRegex(
            session_id,
            re.compile(r"^chat-\d{8}-\d{6}-[a-f0-9]{6}$"),
        )

    def test_new_session_ids_are_unique(self):
        self.assertNotEqual(new_session_id(), new_session_id())


if __name__ == "__main__":
    unittest.main()
