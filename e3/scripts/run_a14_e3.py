#!/usr/bin/env python3
"""Run the A14 E3 MD/RD and C0/C1/C2 baselines and preserve evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shlex
import shutil
import subprocess
import tarfile
import time
from datetime import datetime, timezone
from pathlib import Path


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def tool_version(command: list[str]) -> dict[str, object]:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
        output = (result.stdout or result.stderr).strip().splitlines()
        return {"command": command, "exit_code": result.returncode, "version": output[0] if output else ""}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"command": command, "exit_code": 127, "version": str(exc)}


class Runner:
    def __init__(self, repo: Path, evidence: Path, work: Path) -> None:
        self.repo = repo
        self.evidence = evidence
        self.work = work
        self.commands: list[dict[str, object]] = []
        self.observations: list[dict[str, object]] = []

    def run(self, command: list[str], cwd: Path, log_name: str, timeout: int = 120) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env.update({"LC_ALL": "C", "LANG": "C"})
        started = datetime.now(timezone.utc).isoformat()
        try:
            result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env)
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
            result = subprocess.CompletedProcess(command, 124, stdout, stderr + "\nTIMEOUT\n")
        log_path = self.evidence / log_name
        log_path.write_text(
            f"$ {shlex.join(command)}\n"
            f"cwd={cwd}\n"
            f"started_utc={started}\n"
            f"exit_code={result.returncode}\n\n"
            f"[stdout]\n{result.stdout}\n[stderr]\n{result.stderr}",
            encoding="utf-8",
        )
        self.commands.append(
            {
                "command": command,
                "cwd": str(cwd.relative_to(self.repo)) if cwd.is_relative_to(self.repo) else str(cwd),
                "exit_code": result.returncode,
                "log": log_name,
            }
        )
        return result

    def observe(self, observation_id: str, expected: object, actual: object, passed: bool, basis: str) -> None:
        self.observations.append(
            {"id": observation_id, "expected": expected, "actual": actual, "passed": passed, "basis": basis}
        )

    def app_output(self, cwd: Path, log_name: str) -> tuple[int, str]:
        result = self.run(["./app"], cwd, log_name)
        return result.returncode, result.stdout.strip()

    def export_project(self, label: str, commit: str) -> Path:
        destination = self.work / "versions" / label
        destination.mkdir(parents=True)
        archive = self.work / f"{label}.tar"
        result = self.run(
            ["git", "archive", "--format=tar", f"--output={archive}", commit, "e3/fixtures/commits/project"],
            self.repo,
            f"git-archive-{label}.log",
        )
        if result.returncode != 0:
            raise RuntimeError(f"cannot export {label} at {commit}")
        with tarfile.open(archive) as tf:
            # The archive is produced locally by Git from this trusted repository.
            tf.extractall(destination)
        return destination / "e3" / "fixtures" / "commits" / "project"


def replace_define(path: Path, name: str, value: int, reference: Path) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    updated = [f"#define {name} {value}" if line.startswith(f"#define {name} ") else line for line in lines]
    path.write_text("\n".join(updated) + "\n", encoding="utf-8")
    timestamp = max(time.time(), reference.stat().st_mtime + 2.0)
    os.utime(path, (timestamp, timestamp))


def copy_tree(source: Path, destination: Path) -> Path:
    shutil.copytree(source, destination)
    return destination


def overlay_tree(source: Path, destination: Path) -> None:
    for path in source.rglob("*"):
        relative = path.relative_to(source)
        target = destination / relative
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-a14-e3"))
    args = parser.parse_args()

    repo = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip()).resolve()
    e3 = repo / "e3"
    baseline_path = e3 / "baseline.json"
    if not baseline_path.exists():
        raise SystemExit("e3/baseline.json is missing; create C0/C1/C2 commits first")
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    evidence = e3 / "evidence" / args.run_id
    work = e3 / "work" / args.run_id
    if evidence.exists() or work.exists():
        raise SystemExit(f"run-id already exists: {args.run_id}")
    evidence.mkdir(parents=True)
    work.mkdir(parents=True)
    runner = Runner(repo, evidence, work)

    environment = {
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "tools": {
            "git": tool_version(["git", "--version"]),
            "make": tool_version(["make", "--version"]),
            "cc": tool_version(["cc", "--version"]),
            "python3": tool_version(["python3", "--version"]),
            "strace": tool_version(["strace", "--version"]),
        },
        "repository_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip(),
        "baseline": baseline,
    }
    write_json(evidence / "environment.json", environment)
    shutil.copy2(e3 / "oracle.json", evidence / "oracle.json")
    shutil.copy2(baseline_path, evidence / "baseline.json")

    # Independent MD/RD fixture.
    md_source = e3 / "fixtures" / "md-rd"
    md_work = copy_tree(md_source, work / "md-rd-missing")
    runner.run(["make", "clean"], md_work, "md-01-clean.log")
    initial_make = runner.run(["make"], md_work, "md-02-initial-make.log")
    initial_code, initial_output = runner.app_output(md_work, "md-03-initial-app.log")
    runner.observe("md_initial", {"make_exit": 0, "app_output": "1"}, {"make_exit": initial_make.returncode, "app_exit": initial_code, "app_output": initial_output}, initial_make.returncode == 0 and initial_code == 0 and initial_output == "1", "fixture builds before dependency behavior is exercised")

    replace_define(md_work / "config.h", "VALUE", 2, md_work / "main.o")
    md_incremental = runner.run(["make"], md_work, "md-04-incremental-after-config.log")
    _, md_stale_output = runner.app_output(md_work, "md-05-stale-app.log")
    runner.run(["make", "clean"], md_work, "md-06-clean.log")
    md_clean = runner.run(["make"], md_work, "md-07-clean-rebuild.log")
    _, md_clean_output = runner.app_output(md_work, "md-08-clean-app.log")
    runner.observe("missing_dependency_behavior", {"incremental_output": "1", "clean_output": "2"}, {"incremental_make_exit": md_incremental.returncode, "incremental_output": md_stale_output, "clean_make_exit": md_clean.returncode, "clean_output": md_clean_output}, md_incremental.returncode == 0 and md_stale_output == "1" and md_clean.returncode == 0 and md_clean_output == "2", "config.h is read but absent from main.o prerequisites")

    rd_work = copy_tree(md_source, work / "md-rd-redundant")
    runner.run(["make", "clean"], rd_work, "rd-01-clean.log")
    runner.run(["make"], rd_work, "rd-02-initial-make.log")
    unused = rd_work / "unused.h"
    unused.write_text(unused.read_text(encoding="utf-8") + "/* changed but still unused */\n", encoding="utf-8")
    timestamp = max(time.time(), (rd_work / "main.o").stat().st_mtime + 2.0)
    os.utime(unused, (timestamp, timestamp))
    rd_make = runner.run(["make"], rd_work, "rd-03-after-unused-change.log")
    rd_recompiled = "main.c -o main.o" in rd_make.stdout
    runner.observe("redundant_dependency_behavior", {"recompile": True, "app_output": "1"}, {"make_exit": rd_make.returncode, "recompile": rd_recompiled, "make_output": rd_make.stdout.strip()}, rd_make.returncode == 0 and rd_recompiled, "unused.h is declared but not read, so changing it causes unnecessary compilation")

    fail_work = copy_tree(md_source, work / "negative-missing-header")
    (fail_work / "config.h").unlink()
    runner.run(["make", "clean"], fail_work, "failure-01-clean.log")
    failed_make = runner.run(["make"], fail_work, "failure-02-missing-header.log")
    runner.observe("negative_missing_header", {"make_nonzero": True}, {"make_exit": failed_make.returncode}, failed_make.returncode != 0, "failure log is bound to a concrete source snapshot")

    commits = baseline["versions"]
    c0 = runner.export_project("C0", commits["C0"]["commit"])
    runner.run(["make", "clean"], c0, "c0-01-clean.log")
    c0_make = runner.run(["make"], c0, "c0-02-make.log")
    _, c0_output = runner.app_output(c0, "c0-03-app.log")
    runner.observe("c0_clean", {"make_exit": 0, "output": "10", "findings": []}, {"make_exit": c0_make.returncode, "output": c0_output}, c0_make.returncode == 0 and c0_output == "10", "C0 source and declared project dependencies agree")

    c1 = runner.export_project("C1", commits["C1"]["commit"])
    runner.run(["make", "clean"], c1, "c1-01-clean.log")
    c1_make = runner.run(["make"], c1, "c1-02-make.log")
    _, c1_output = runner.app_output(c1, "c1-03-app.log")
    replace_define(c1 / "feature.h", "FEATURE", 5, c1 / "main.o")
    c1_incremental = runner.run(["make"], c1, "c1-04-incremental-after-feature.log")
    _, c1_stale = runner.app_output(c1, "c1-05-stale-app.log")
    runner.run(["make", "clean"], c1, "c1-06-clean.log")
    c1_clean = runner.run(["make"], c1, "c1-07-clean-rebuild.log")
    _, c1_clean_output = runner.app_output(c1, "c1-08-clean-app.log")
    runner.observe("c1_missing_feature", {"base_clean_output": "12", "after_feature_incremental": "12", "after_feature_clean": "15"}, {"base_make_exit": c1_make.returncode, "base_clean_output": c1_output, "incremental_make_exit": c1_incremental.returncode, "after_feature_incremental": c1_stale, "clean_make_exit": c1_clean.returncode, "after_feature_clean": c1_clean_output}, c1_make.returncode == 0 and c1_output == "12" and c1_incremental.returncode == 0 and c1_stale == "12" and c1_clean.returncode == 0 and c1_clean_output == "15", "C1 reads feature.h but leaves it out of main.o prerequisites")

    c1_for_c2 = runner.export_project("C1-for-C2", commits["C1"]["commit"])
    runner.run(["make", "clean"], c1_for_c2, "c2-01-c1-clean.log")
    runner.run(["make"], c1_for_c2, "c2-02-c1-build.log")
    _, c2_before = runner.app_output(c1_for_c2, "c2-03-c1-app.log")
    c2_source = runner.export_project("C2-source", commits["C2"]["commit"])
    overlay_tree(c2_source, c1_for_c2)
    older = (c1_for_c2 / "main.o").stat().st_mtime - 5.0
    for name in ("main.c", "config.h", "feature.h"):
        os.utime(c1_for_c2 / name, (older, older))
    c2_incremental = runner.run(["make"], c1_for_c2, "c2-04-incremental.log")
    _, c2_incremental_output = runner.app_output(c1_for_c2, "c2-05-incremental-app.log")
    runner.run(["make", "clean"], c1_for_c2, "c2-06-clean.log")
    c2_clean = runner.run(["make"], c1_for_c2, "c2-07-clean-rebuild.log")
    _, c2_clean_output = runner.app_output(c1_for_c2, "c2-08-clean-app.log")
    runner.run(["make", "-n", "-B", "main.o"], c2_source, "c2-09-forced-command.log")
    runner.observe("c2_command_change", {"before": "12", "incremental": "12", "clean": "19"}, {"before": c2_before, "incremental_make_exit": c2_incremental.returncode, "incremental": c2_incremental_output, "clean_make_exit": c2_clean.returncode, "clean": c2_clean_output}, c2_before == "12" and c2_incremental.returncode == 0 and c2_incremental_output == "12" and c2_clean.returncode == 0 and c2_clean_output == "19", "ordinary Make timestamp logic does not rebuild merely because CFLAGS changed")

    trace_work = copy_tree(md_source, work / "linux-trace")
    runner.run(["make", "clean"], trace_work, "trace-01-clean.log")
    trace_result = runner.run(["strace", "-ff", "-o", "trace.log", "-e", "trace=%file,%process", "make"], trace_work, "trace-02-strace-make.log", timeout=180)
    runner.run(["make", "-pn"], trace_work, "trace-03-make-database.log", timeout=180)
    trace_files = sorted(trace_work.glob("trace.log*"))
    trace_text_parts = []
    for path in trace_files:
        trace_text_parts.append(f"===== {path.name} =====\n{path.read_text(encoding='utf-8', errors='replace')}")
    trace_text = "\n".join(trace_text_parts)
    (evidence / "trace-raw.log").write_text(trace_text, encoding="utf-8")
    config_hits = sum(1 for line in trace_text.splitlines() if "config.h" in line)
    runner.observe("linux_raw_trace", {"strace_exit": 0, "config_h_hits_min": 1}, {"strace_exit": trace_result.returncode, "trace_files": len(trace_files), "config_h_hits": config_hits}, trace_result.returncode == 0 and config_hits > 0, "raw file/process trace proves the compiler accessed config.h; it is not presented as a complete detector")

    passed = sum(1 for item in runner.observations if item["passed"])
    summary = {
        "schema_version": "1.0",
        "run_id": args.run_id,
        "source": "REAL_EXECUTION_WITH_INSTRUCTOR_ORACLE",
        "passed": passed == len(runner.observations),
        "checks_passed": passed,
        "checks_total": len(runner.observations),
        "observations": runner.observations,
        "limitations": [
            "The findings in oracle.json are human labels, not BuildChecker or EChecker output.",
            "strace evidence records raw accesses only; process attribution, graph normalization and automatic MD/RD inference remain later implementation work.",
            "Cross-group live-service integration is deferred to E12.",
        ],
    }
    write_json(evidence / "commands.json", runner.commands)
    write_json(evidence / "observations.json", summary)

    checksum_lines = []
    for path in sorted(evidence.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.txt":
            checksum_lines.append(f"{sha256_file(path)}  {path.relative_to(evidence).as_posix()}")
    (evidence / "SHA256SUMS.txt").write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")
    print(f"EVIDENCE_DIR={evidence}")
    print(f"PASS={summary['passed']} ({passed}/{len(runner.observations)})")
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
