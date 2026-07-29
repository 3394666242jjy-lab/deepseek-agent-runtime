import unittest

from mini_agent.tools.base import ToolError
from mini_agent.tools.calculator import safe_calculate


class CalculatorTests(unittest.TestCase):
    def test_arithmetic_and_functions(self):
        self.assertEqual(safe_calculate("(12 + 3) * 2"), 30)
        self.assertEqual(safe_calculate("sqrt(81) + abs(-2)"), 11)

    def test_blocks_code_execution(self):
        with self.assertRaises(ToolError):
            safe_calculate("__import__('os').system('echo unsafe')")

    def test_division_by_zero_is_a_tool_error(self):
        with self.assertRaisesRegex(ToolError, "除数不能为零"):
            safe_calculate("1 / 0")


if __name__ == "__main__":
    unittest.main()
