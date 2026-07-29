from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import Settings
from .llm import LLMError
from .runtime import AgentRuntime


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mini-agent",
        description="从零实现的 DeepSeek 最小 Agent Runtime",
    )
    parser.add_argument("--env", default=".env", help=".env 文件路径")
    sub = parser.add_subparsers(dest="command", required=True)

    ask = sub.add_parser("ask", help="单次提问（状态仍会保存）")
    ask.add_argument("message", help="用户输入")
    ask.add_argument("--session", default="default", help="session id")
    ask.add_argument("--show-trace", action="store_true", help="显示本次工具调用")

    chat = sub.add_parser("chat", help="进入交互式对话")
    chat.add_argument("--session", default="default", help="session id")
    chat.add_argument("--show-trace", action="store_true", help="每轮显示工具调用")

    sub.add_parser("sessions", help="列出已保存 session")

    trace = sub.add_parser("trace", help="查看 session 执行日志")
    trace.add_argument("--session", default="default", help="session id")
    trace.add_argument("--limit", type=int, default=30, help="最多显示条数")
    return parser


def _print_result(result: object, show_trace: bool) -> None:
    print(getattr(result, "answer"))
    if show_trace and getattr(result, "tool_calls"):
        print("\n--- tool trace ---")
        print(json.dumps(getattr(result, "tool_calls"), ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    settings = Settings.from_env(Path(args.env))

    if args.command in {"ask", "chat"}:
        try:
            settings.require_api_key()
        except ValueError as exc:
            print(f"配置错误：{exc}", file=sys.stderr)
            return 2

    runtime = AgentRuntime(settings)
    try:
        if args.command == "sessions":
            print(json.dumps(runtime.sessions.list_sessions(), ensure_ascii=False, indent=2))
            return 0
        if args.command == "trace":
            records = runtime.traces.read(args.session, max(1, args.limit))
            print(json.dumps(records, ensure_ascii=False, indent=2))
            return 0
        if args.command == "ask":
            _print_result(runtime.run(args.session, args.message), args.show_trace)
            return 0

        print(f"session={args.session}。输入 /exit 退出，/trace 查看最近日志。")
        while True:
            try:
                text = input("you> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not text:
                continue
            if text in {"/exit", "/quit"}:
                break
            if text == "/trace":
                print(
                    json.dumps(
                        runtime.traces.read(args.session, 20),
                        ensure_ascii=False,
                        indent=2,
                    )
                )
                continue
            result = runtime.run(args.session, text)
            print("agent> ", end="")
            _print_result(result, args.show_trace)
        return 0
    except (LLMError, ValueError) as exc:
        print(f"运行失败：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
