#!/usr/bin/env python3
"""Verify A14 E3 evidence checksums, observations, command logs and Git baselines."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True)


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", nargs="?", default="e3/evidence/20261008-a14-e3")
    args = parser.parse_args()
    evidence = Path(args.evidence).resolve()
    if not evidence.is_dir():
        fail(f"evidence directory not found: {evidence}")

    required = {"baseline.json", "commands.json", "environment.json", "observations.json", "oracle.json", "SHA256SUMS.txt"}
    missing = sorted(name for name in required if not (evidence / name).is_file())
    if missing:
        fail(f"missing required files: {missing}")

    expected_files: set[str] = set()
    for line in (evidence / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        if not match:
            fail(f"invalid checksum line: {line!r}")
        expected, relative = match.groups()
        path = evidence / relative
        if not path.is_file():
            fail(f"checksummed file missing: {relative}")
        if sha256_file(path) != expected:
            fail(f"checksum mismatch: {relative}")
        expected_files.add(relative)

    actual_files = {path.relative_to(evidence).as_posix() for path in evidence.rglob("*") if path.is_file() and path.name != "SHA256SUMS.txt"}
    if expected_files != actual_files:
        fail(f"checksum inventory mismatch: missing={sorted(actual_files - expected_files)}, extra={sorted(expected_files - actual_files)}")

    observations = json.loads((evidence / "observations.json").read_text(encoding="utf-8"))
    items = observations.get("observations", [])
    if not observations.get("passed") or observations.get("checks_passed") != observations.get("checks_total"):
        fail("observation summary is not fully passing")
    if not items or not all(item.get("passed") is True for item in items):
        fail("one or more observations failed")

    commands = json.loads((evidence / "commands.json").read_text(encoding="utf-8"))
    for item in commands:
        log = item.get("log")
        if not isinstance(log, str) or not (evidence / log).is_file():
            fail(f"command log missing: {log!r}")

    baseline = json.loads((evidence / "baseline.json").read_text(encoding="utf-8"))
    repo = next((path for path in (evidence, *evidence.parents) if (path / ".git").exists()), None)
    if repo is not None:
        ordered = []
        for label in ("C0", "C1", "C2"):
            record = baseline["versions"][label]
            commit = record["commit"]
            tag = record["tag"]
            if not re.fullmatch(r"[0-9a-f]{40}", commit):
                fail(f"{label} is not a full commit SHA")
            tag_result = git(repo, "rev-parse", f"{tag}^{{}}")
            if tag_result.returncode != 0 or tag_result.stdout.strip() != commit:
                fail(f"{tag} does not resolve to {commit}")
            ordered.append(commit)
        for older, newer in zip(ordered, ordered[1:]):
            if git(repo, "merge-base", "--is-ancestor", older, newer).returncode != 0:
                fail(f"baseline history is not ordered: {older} -> {newer}")

    print(
        "PASS: "
        f"evidence_files={len(actual_files) + 1}, "
        f"checks={len(items)}, commands={len(commands)}, baselines=3"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
