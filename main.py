"""Simple interactive entry point.

Run:
    python main.py
    python main.py --session my-window --show-trace
"""

from __future__ import annotations

import argparse

from mini_agent.cli import main as cli_main


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="启动 DeepSeek Agent 交互式终端"
    )
    parser.add_argument("--session", default="default", help="会话名称")
    parser.add_argument("--env", default=".env", help=".env 文件路径")
    parser.add_argument(
        "--show-trace",
        action="store_true",
        help="每轮回答后显示工具调用详情",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    cli_args = [
        "--env",
        args.env,
        "chat",
        "--session",
        args.session,
    ]
    if args.show_trace:
        cli_args.append("--show-trace")
    return cli_main(cli_args)


if __name__ == "__main__":
    raise SystemExit(main())
