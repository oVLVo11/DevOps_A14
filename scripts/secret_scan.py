#!/usr/bin/env python3
"""检查工作区、Git 历史和镜像中的疑似密钥。"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

PATTERNS = [
    ("LLM/API Key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}")),
    ("私钥", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    ("GitHub Token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}")),
    (
        "密钥赋值",
        re.compile(
            r"(?i)\b[\w.-]*(?:api[_-]?key|secret|token|passw(?:or)?d)\b\s*[:=]\s*[\"']?([^\s\"'#,;]{12,})"
        ),
    ),
]
PLACEHOLDER = re.compile(r"(?i)replace|your[_-]|example|changeme|xxxx|<[^>]*>|\$\{|\$\(|\*\*\*")
SKIP_DIRS = {".git", "work", "__pycache__", ".venv", "node_modules"}


def mask(value):
    return value[:4] + "***" if len(value) > 4 else "***"


def scan_text(text, where):
    hits = []
    for number, line in enumerate(text.splitlines(), 1):
        for name, pattern in PATTERNS:
            for match in pattern.finditer(line):
                value = match.group(match.lastindex or 0)
                if name == "密钥赋值" and PLACEHOLDER.search(value):
                    continue
                hits.append(f"{where}:{number}  {name}  {mask(value)}")
    return hits


def git(root, *args):
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def files(root):
    process = git(root, "ls-files")
    if process.returncode == 0:
        return [root / name for name in process.stdout.splitlines()], True
    output = []
    for directory, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name not in SKIP_DIRS]
        output += [Path(directory) / name for name in filenames]
    return output, False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--history", action="store_true")
    parser.add_argument("--image")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    hits = []

    paths, in_git = files(root)
    for path in paths:
        relative = path.relative_to(root).as_posix()
        if path.name == ".env" or (path.name.startswith(".env.") and path.name != ".env.example"):
            if in_git:
                hits.append(f"{relative}  .env 被 Git 跟踪（应立即作废其中的 Key）")
            continue
        try:
            if path.stat().st_size <= 2_000_000:
                hits += scan_text(path.read_text(encoding="utf-8", errors="ignore"), relative)
        except OSError:
            pass

    env = root / ".env"
    if env.exists() and os.name == "posix" and env.stat().st_mode & 0o077:
        hits.append(".env 权限过宽：执行 chmod 600 .env")

    if args.history and in_git:
        hits += scan_text(git(root, "log", "--all", "-p", "--no-color").stdout, "git-history")
    if args.image:
        commands = (
            (["docker", "history", "--no-trunc", "--format", "{{.CreatedBy}}", args.image], "image-history"),
            (
                [
                    "docker",
                    "image",
                    "inspect",
                    "--format",
                    "{{range .Config.Env}}{{println .}}{{end}}",
                    args.image,
                ],
                "image-env",
            ),
        )
        for command, where in commands:
            process = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            if process.returncode != 0:
                print(f"无法检查镜像 {args.image}：{process.stderr.strip()}", file=sys.stderr)
                raise SystemExit(2)
            hits += scan_text(process.stdout, where)

    for hit in hits:
        print("FOUND  " + hit)
    print(
        f"密钥检查：{'未发现问题' if not hits else f'发现 {len(hits)} 处疑似泄露'}"
        f"（文件 {len(paths)} 个{'，含 Git 历史' if args.history else ''}"
        f"{'，含镜像 ' + args.image if args.image else ''}）"
    )
    raise SystemExit(1 if hits else 0)


if __name__ == "__main__":
    main()
