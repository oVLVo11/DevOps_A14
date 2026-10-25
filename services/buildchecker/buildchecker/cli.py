"""BuildChecker command line entry point."""

import argparse
import json

from . import __version__
from .smoke import run_smoke
from .fullcheck import full_check


def build_parser():
    parser = argparse.ArgumentParser(prog="buildchecker")
    subcommands = parser.add_subparsers(dest="cmd", required=True)
    subcommands.add_parser("version", help="打印版本")
    smoke_parser = subcommands.add_parser(
        "smoke", help="E4 冒烟测试：在容器里用 strace 跟踪 E3 md-rd 样例"
    )
    smoke_parser.add_argument("--fixture", default="fixtures/md-rd")
    full_parser = subcommands.add_parser("full-check", help="从真实构建生成依赖图与 MD/RD 报告")
    full_parser.add_argument("--fixture", default="fixtures/md-rd")
    full_parser.add_argument("--out", required=True)
    full_parser.add_argument("--clean-command", default="make clean")
    full_parser.add_argument("--build-command", default="make app")
    full_parser.add_argument("--timeout", type=int, default=120)
    full_parser.add_argument("--fail-on-findings", action="store_true")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.cmd == "version":
        print(f"buildchecker {__version__}")
        return 0
    if args.cmd == "smoke":
        result = run_smoke(args.fixture)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["passed"] else 1
    try:
        if args.timeout <= 0:
            raise ValueError("Timeout must be positive")
        result = full_check(args.fixture, args.out, args.clean_command, args.build_command, args.timeout)
    except (ValueError, OSError) as exc:
        print(json.dumps({"status": "FAILED", "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    # A finished analysis can contain dependency errors. Only the optional
    # quality gate turns those findings into a nonzero CLI exit status.
    return 0 if result["status"] == "SUCCEEDED" and not (args.fail_on_findings and result["findings"]) else 1
