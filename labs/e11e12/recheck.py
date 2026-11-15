"""A14 recheck of a B14 candidate patch against the exact target commit."""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import uuid
from pathlib import Path

from a_track import ROOT, save, snapshot

sys.path.insert(0, str(ROOT / "validator"))
from validate import schema_check  # noqa: E402


def check_md_report(report, repo_url, commit, configuration_id):
    schema_check(report, "Report")
    if report["repository"] != {"url": repo_url, "commit": commit}:
        raise ValueError("STALE_REPORT: repository or target commit differs")
    if report["configuration_id"] != configuration_id:
        raise ValueError("CONFIGURATION_MISMATCH")
    findings = report["findings"]
    if not findings or any(f["type"] != "MISSING" or f["commit"] != commit for f in findings):
        raise ValueError("MD_ONLY_REQUIRED")
    if len({f["finding_id"] for f in findings}) != len(findings):
        raise ValueError("Duplicate finding IDs")
    return {(f["target"], f["dependency"]) for f in findings}


def check_patch(patch, expected_sha256, makefile_path):
    content = patch.read_bytes()
    if hashlib.sha256(content).hexdigest() != expected_sha256:
        raise ValueError("ARTIFACT_HASH_MISMATCH")
    text = content.decode("utf-8")
    if text.count("diff --git ") != 1:
        raise ValueError("Patch must change exactly one Makefile")
    escaped = re.escape(makefile_path.as_posix())
    if not re.search(r"^diff --git a/" + escaped + r" b/" + escaped + r"$", text, re.M):
        raise ValueError("Patch path differs from the target Makefile")
    return text


def execute(argv, cwd, log, timeout):
    result = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    log.write_text(result.stdout + result.stderr, encoding="utf-8")
    if result.returncode:
        raise ValueError(f"Command failed ({result.returncode}): {' '.join(argv)}; see {log}")
    return result.stdout.strip()


def recheck(repo, target, project_path, patch, patch_uri, patch_sha256, md_report,
            repo_url, configuration_id, expected_output, out):
    if out.exists():
        raise ValueError("Output already exists; choose a new evidence directory")
    if not re.fullmatch(r"[0-9a-f]{40}", target):
        raise ValueError("Complete target SHA required")
    project_path = Path(project_path)
    if project_path.is_absolute() or ".." in project_path.parts:
        raise ValueError("Project path must stay within the repository")
    if not re.fullmatch(r"artifact://[a-z0-9-]+/[A-Za-z0-9_-]+/[A-Za-z0-9._-]+", patch_uri):
        raise ValueError("Invalid patch URI")
    requested = check_md_report(md_report, repo_url, target, configuration_id)
    makefile_path = project_path / "Makefile"
    check_patch(patch, patch_sha256, makefile_path)
    out.mkdir(parents=True)
    try:
        source = snapshot(repo, target, out / "target-project")
        project = source / project_path
        if not (project / "Makefile").is_file():
            raise ValueError("Target Makefile missing")
        execute(["git", "apply", "--check", str(patch)], source, out / "patch-check.log", 30)
        execute(["git", "apply", str(patch)], source, out / "patch-apply.log", 30)
        execute(["make", "clean"], project, out / "clean.log", 120)
        execute(["make", "app"], project, out / "build.log", 120)
        observed = execute([str(project / "app")], project, out / "verify.log", 30)
        if observed != expected_output:
            raise ValueError("Program output differs from expected value")
        sys.path.insert(0, str(ROOT / "labs/e8e10/environment/services/buildchecker"))
        from buildchecker.fullcheck import full_check
        result = full_check(project, out / "full-recheck")
        if result["status"] != "SUCCEEDED":
            raise ValueError("BuildChecker recheck failed: " + str(result.get("error")))
        remaining = [f for f in result["findings"] if f["type"] == "MISSING"]
        present = {(f["target"], f["dependency"]) for f in result["findings"]}
        if any(pair in present for pair in requested):
            raise ValueError("Input MD remains after patch")
        payload = {"repository": {"url": repo_url, "commit": target},
                   "configuration_id": configuration_id, "producer_job_id": "job-" + uuid.uuid4().hex,
                   "patch_uri": patch_uri, "patch_sha256": patch_sha256,
                   "remaining_missing": len(remaining), "source": "DYNAMIC_TRACE",
                   "test_output": observed, "status": "SUCCEEDED" if not remaining else "FAILED",
                   "note": "A14 local recheck; B14 makes the final candidate decision. Real execution is not representable by the manual-only E2 RecheckReport schema."}
        save(out / "recheck.json", payload)
        return payload
    except Exception as exc:
        save(out / "failure.json", {"status": "FAILED", "reason": str(exc), "patch_uri": patch_uri})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--project-path", type=Path, default=Path("."))
    parser.add_argument("--patch", type=Path, required=True)
    parser.add_argument("--patch-uri", required=True)
    parser.add_argument("--patch-sha256", required=True)
    parser.add_argument("--md-report", type=Path, required=True)
    parser.add_argument("--repository-url", required=True)
    parser.add_argument("--configuration-id", required=True)
    parser.add_argument("--expected-output", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = json.loads(args.md_report.read_text(encoding="utf-8"))
    print(json.dumps(recheck(args.repo.resolve(), args.target, args.project_path,
                             args.patch.resolve(), args.patch_uri, args.patch_sha256, report,
                             args.repository_url, args.configuration_id, args.expected_output,
                             args.out.resolve()), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
