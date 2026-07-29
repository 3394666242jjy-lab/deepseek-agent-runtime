import unittest

from mini_agent.llm import LLMError, parse_model_message


class ModelParserTests(unittest.TestCase):
    def test_native_function_call(self):
        decision = parse_model_message(
            {
                "content": None,
                "reasoning_content": "需要计算",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "calculator",
                            "arguments": '{"expression":"6*7"}',
                        },
                    }
                ],
            }
        )
        self.assertEqual(decision.reasoning, "需要计算")
        self.assertEqual(decision.tool_calls[0].name, "calculator")
        self.assertEqual(decision.tool_calls[0].arguments, {"expression": "6*7"})

    def test_json_fallback_call(self):
        decision = parse_model_message(
            {
                "content": (
                    '```json\n{"thought":"查一下","tool_call":'
                    '{"name":"search","arguments":{"query":"agent"}}}\n```'
                )
            }
        )
        self.assertEqual(decision.reasoning, "查一下")
        self.assertEqual(decision.tool_calls[0].name, "search")

    def test_json_fallback_final(self):
        decision = parse_model_message(
            {"content": '{"thought":"完成","final":"答案是 42"}'}
        )
        self.assertEqual(decision.content, "答案是 42")

    def test_invalid_arguments(self):
        with self.assertRaises(LLMError):
            parse_model_message(
                {
                    "tool_calls": [
                        {
                            "id": "bad",
                            "function": {
                                "name": "calculator",
                                "arguments": "{bad json",
                            },
                        }
                    ]
                }
            )


if __name__ == "__main__":
    unittest.main()
