"""BuildChecker 命令行入口。"""

import argparse
import json

from . import __version__
from .smoke import run_smoke


def build_parser():
    parser = argparse.ArgumentParser(prog="buildchecker")
    subcommands = parser.add_subparsers(dest="cmd", required=True)
    subcommands.add_parser("version", help="打印版本")
    smoke_parser = subcommands.add_parser(
        "smoke", help="E4 冒烟测试：在容器里用 strace 跟踪 E3 md-rd 样例"
    )
    smoke_parser.add_argument("--fixture", default="fixtures/md-rd")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.cmd == "version":
        print(f"buildchecker {__version__}")
        return 0
    result = run_smoke(args.fixture)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1
