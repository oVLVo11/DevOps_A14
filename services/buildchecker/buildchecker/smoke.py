"""确认容器内的 make、gcc、strace 能配合工作的 E4 冒烟测试。"""

import re
import shutil
import subprocess
import tempfile
from pathlib import Path


def run(cmd, cwd):
    process = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=120)
    return process.returncode, process.stdout + process.stderr


def files_opened(trace_text, name):
    """返回跟踪记录中通过 open/openat 打开 name 的行。"""
    pattern = re.compile(r'\bopen(?:at)?\(.*"(?:[^"]*/)?' + re.escape(name) + r'"')
    return [line for line in trace_text.splitlines() if pattern.search(line)]


def run_smoke(fixture):
    source = Path(fixture)
    with tempfile.TemporaryDirectory(prefix="e4-smoke-") as temp_dir:
        work = Path(temp_dir) / source.name
        shutil.copytree(source, work)
        tools = {
            name: run([name, "--version"], work)[1].splitlines()[0]
            for name in ("make", "gcc", "strace")
        }
        code, output = run(
            ["strace", "-f", "-o", "trace.txt", "-e", "trace=%file,%process", "make"],
            work,
        )
        trace_path = work / "trace.txt"
        trace = trace_path.read_text() if trace_path.exists() else ""
        _, app_output = run(["./app"], work) if code == 0 else (None, "")
        config = files_opened(trace, "config.h")
        unused = files_opened(trace, "unused.h")
    return {
        "fixture": str(source),
        "tools": tools,
        "make_exit_code": code,
        "make_output": output.strip().splitlines()[-5:],
        "app_output": app_output.strip(),
        "trace_lines": len(trace.splitlines()),
        "config_h_opened": config[:3],
        "unused_h_opened": unused[:3],
        "passed": code == 0 and bool(config),
        "note": "只说明环境可用；config.h / unused.h 的结论留到 E5 由各组自己推导",
    }
