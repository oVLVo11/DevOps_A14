"""A14 E11 integration and E12 handoff for the supported C/Make teaching profile.

The incremental scan is the E8-E10 GCC -MM approximation. The target clean
build is an oracle; neither step claims to implement EChecker's incremental
system-call trace merge or to establish a performance improvement.
"""
import argparse
import hashlib
import json
import re
import shlex
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "labs/e8e10"))
from lab import scan  # noqa: E402


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def command(*args, cwd):
    return subprocess.check_output(args, cwd=cwd, text=True, stderr=subprocess.STDOUT).strip()


def snapshot(repo, commit, destination):
    resolved = command("git", "rev-parse", "--verify", commit + "^{commit}", cwd=repo)
    if resolved != commit:
        raise ValueError("A complete 40-character commit SHA is required")
    command("git", "clone", "--no-hardlinks", "--no-checkout", str(repo), str(destination), cwd=repo)
    command("git", "checkout", "--detach", commit, cwd=destination)
    if command("git", "rev-parse", "HEAD", cwd=destination) != commit:
        raise ValueError("Checked-out commit does not match the request")
    return destination


def object_edges(edges, targets):
    return {target: sorted({edge["dependency"] for edge in edges if edge["target"] == target})
            for target in targets}


def finding_keys(findings, targets):
    return sorted((f["type"], f["target"], f["dependency"]) for f in findings
                  if f["target"] in targets)


def scan_project(project, old=None):
    """Use E8-E10 unchanged for its profile; adapt A14's E3 one-object project."""
    makefile = (project / "Makefile").read_text(encoding="utf-8")
    if re.search(r"^helper\.o:", makefile, re.M):
        return scan(project, old)
    if not (project / "main.c").is_file() or not re.search(r"^main\.o:", makefile, re.M):
        raise ValueError("UNSUPPORTED_PROJECT: expected explicit main.o rule")
    flags_match = re.search(r"^CFLAGS\s*=\s*(.*)$", makefile, re.M)
    flags = flags_match.group(1).strip() if flags_match else ""
    declaration = re.search(r"^main\.o:\s*([^\n]*)$", makefile, re.M).group(1).split()
    if any("$" in d or "%" in d or "|" in d for d in declaration):
        raise ValueError("UNSUPPORTED_RULE: expanded E3 prerequisites required")
    files = {p.name: p.read_text(encoding="utf-8") for p in sorted(project.glob("*"))
             if p.suffix in (".c", ".h")}
    key = {"directives": {name: [line for line in contents.splitlines()
                               if line.lstrip().startswith("#")] for name, contents in files.items()},
           "recipes": [line for line in makefile.splitlines() if line.startswith("\t")],
           "flags": flags, "compiler": command("cc", "--version", cwd=project).splitlines()[0]}
    if old is not None and old["key"] == key:
        actual, refreshed, reused = old["actual"], [], ["main.o"]
    else:
        output = command("cc", *shlex.split(flags), "-MM", "-MT", "main.o", "main.c", cwd=project)
        actual = {"main.o": sorted(set(output.replace("\\\n", " ").split(":", 1)[1].split()))}
        refreshed, reused = ["main.o"], []
    declared = {"main.o": sorted(set(declaration))}
    findings = [{"type": kind, "target": "main.o", "dependency": dep}
                for kind, deps in (("MISSING", set(actual["main.o"]) - set(declared["main.o"])),
                                   ("REDUNDANT", set(declared["main.o"]) - set(actual["main.o"])))
                for dep in sorted(deps)]
    previous = {(f["type"], f["target"], f["dependency"]) for f in old["findings"]} if old else set()
    current = {(f["type"], f["target"], f["dependency"]) for f in findings}
    return {"schema_version": "e8e10-1", "profile": "A14_E3_EXPLICIT_SINGLE_OBJECT",
            "commit": command("git", "rev-parse", "HEAD", cwd=project), "key": key,
            "actual": actual, "declared": declared, "findings": findings,
            "added": [list(x) for x in sorted(current - previous)],
            "resolved": [list(x) for x in sorted(previous - current)],
            "refreshed": refreshed, "reused": reused}


def line_for_target(makefile, target):
    for number, line in enumerate(makefile.read_text(encoding="utf-8").splitlines(), 1):
        if re.match(r"^" + re.escape(target) + r"\s*:", line):
            return number
    raise ValueError("Unsupported Make rule: " + target)


def report(repo_url, commit, configuration_id, job_id, findings, makefile, evidence_kind, targets):
    output = []
    for finding in findings:
        target, dependency, kind = finding["target"], finding["dependency"], finding["type"]
        if target not in targets:
            continue
        # The commit is deliberately excluded so a finding keeps its identity.
        identity = json.dumps([repo_url, configuration_id, kind, target, dependency, "Makefile"],
                              ensure_ascii=False, separators=(",", ":"))
        output.append({
            "finding_id": "a14-" + hashlib.sha256(identity.encode()).hexdigest()[:24],
            "type": kind, "target": target, "dependency": dependency, "commit": commit,
            "detector": "BUILDCHECKER_TEACHING" if evidence_kind == "DYNAMIC_TRACE" else "ECHECKER_GCC_MM_TEACHING",
            "location": {"path": "Makefile", "line": line_for_target(makefile, target)},
            "evidence": {"kind": evidence_kind,
                         "description": "Project-local observed build read and Make database comparison" if evidence_kind == "DYNAMIC_TRACE"
                         else "Historical BuildChecker graph updated by GCC -MM and conservative signatures"},
        })
    return {"schema_version": "1.0", "repository": {"url": repo_url, "commit": commit},
            "configuration_id": configuration_id, "producer_job_id": job_id,
            "findings": sorted(output, key=lambda f: f["finding_id"])}


def graph(repo_url, commit, configuration_id, job_id, kind, edges, source):
    simple = sorted(({"target": edge["target"], "dependency": edge["dependency"]} for edge in edges),
                    key=lambda edge: (edge["target"], edge["dependency"]))
    nodes = sorted({name for edge in simple for name in edge.values()})
    return {"schema_version": "1.0", "repository": {"url": repo_url, "commit": commit},
            "configuration_id": configuration_id, "producer_job_id": job_id,
            "kind": kind, "nodes": nodes, "edges": simple, "source": source}


def publish(out, job_id, name, kind, payload, repo_url, commit, configuration_id, manifest):
    path = out / "artifacts" / "a14-check" / job_id / name
    save(path, payload)
    uri = f"artifact://a14-check/{job_id}/{name}"
    record = {"artifact_id": job_id + "-" + name, "type": kind, "uri": uri,
              "media_type": "application/json", "producer_job_id": job_id,
              "repository_url": repo_url, "commit": commit,
              "configuration_id": configuration_id,
              "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    manifest[uri] = {"path": path.relative_to(out).as_posix(), "artifact": record}
    return record


def verify_bundle(out):
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))["artifacts"]
    allowed = (out / "artifacts").resolve()
    for uri, item in manifest.items():
        path = (out / item["path"]).resolve()
        if not path.is_relative_to(allowed) or path.is_symlink() or not path.is_file():
            raise ValueError("Unsafe or missing artifact: " + uri)
        record = item["artifact"]
        if record["uri"] != uri or hashlib.sha256(path.read_bytes()).hexdigest() != record["sha256"]:
            raise ValueError("Artifact identity or hash mismatch: " + uri)
    return len(manifest)


def run(repo, base, target, out, repo_url, configuration_id, project_path=Path(".")):
    if out.exists():
        raise ValueError("Output already exists; choose a new evidence directory")
    if not re.fullmatch(r"[0-9a-f]{40}", base) or not re.fullmatch(r"[0-9a-f]{40}", target) or base == target:
        raise ValueError("Distinct complete base and target SHA values are required")
    if not repo_url or not configuration_id:
        raise ValueError("Repository URL and configuration ID are required")
    project_path = Path(project_path)
    if project_path.is_absolute() or ".." in project_path.parts:
        raise ValueError("Project path must stay within the repository")
    command("git", "merge-base", "--is-ancestor", base, target, cwd=repo)
    out.mkdir(parents=True)
    try:
        base_project = snapshot(repo, base, out / "base-project") / project_path
        target_project = snapshot(repo, target, out / "target-project") / project_path
        if not base_project.is_dir() or not target_project.is_dir():
            raise ValueError("Project path does not exist in both commits")
        targets = ("main.o", "helper.o") if (base_project / "helper.c").is_file() else ("main.o",)
        sys.path.insert(0, str(ROOT / "labs/e8e10/environment/services/buildchecker"))
        from buildchecker.fullcheck import full_check

        base_full = full_check(base_project, out / "baseline-full")
        if base_full["status"] != "SUCCEEDED":
            raise ValueError("BuildChecker baseline failed: " + str(base_full.get("error")))
        baseline = scan_project(base_project)
        base_actual = json.loads((out / "baseline-full/actual-graph.json").read_text(encoding="utf-8"))
        if object_edges(base_actual, targets) != baseline["actual"]:
            raise ValueError("BuildChecker and GCC baseline graphs differ")
        baseline["actual"] = object_edges(base_actual, targets)
        save(out / "baseline-cache.json", baseline)

        incremental = scan_project(target_project, baseline)
        save(out / "incremental-report.json", incremental)
        target_full = full_check(target_project, out / "target-full")
        if target_full["status"] != "SUCCEEDED":
            raise ValueError("BuildChecker target check failed: " + str(target_full.get("error")))
        target_actual = json.loads((out / "target-full/actual-graph.json").read_text(encoding="utf-8"))
        target_declared = json.loads((out / "target-full/declared-graph.json").read_text(encoding="utf-8"))
        equal = {"actual": object_edges(target_actual, targets) == incremental["actual"],
                 "declared": object_edges(target_declared, targets) == incremental["declared"],
                 "findings": finding_keys(target_full["findings"], targets) == finding_keys(incremental["findings"], targets)}
        save(out / "comparison.json", equal)
        if not all(equal.values()):
            raise ValueError("Incremental/target full comparison failed")

        manifest = {}
        baseline_job, target_job = "job-" + uuid.uuid4().hex, "job-" + uuid.uuid4().hex
        base_report = report(repo_url, base, configuration_id, baseline_job, base_full["findings"],
                             base_project / "Makefile", "DYNAMIC_TRACE", targets)
        target_report = report(repo_url, target, configuration_id, target_job, incremental["findings"],
                               target_project / "Makefile", "STATIC_INFERENCE", targets)
        md_report = {**target_report, "findings": [f for f in target_report["findings"] if f["type"] == "MISSING"]}
        if not md_report["findings"]:
            raise ValueError("No MD to hand off to B14")
        sys.path.insert(0, str(ROOT / "validator"))
        from validate import schema_check
        for checked in (base_report, target_report, md_report):
            schema_check(checked, "Report")
        base_records = [
            publish(out, baseline_job, "actual.json", "ACTUAL_GRAPH",
                    graph(repo_url, base, configuration_id, baseline_job, "ACTUAL_GRAPH", base_actual, "DYNAMIC_TRACE"),
                    repo_url, base, configuration_id, manifest),
            publish(out, baseline_job, "declared.json", "DECLARED_GRAPH",
                    graph(repo_url, base, configuration_id, baseline_job, "DECLARED_GRAPH",
                          json.loads((out / "baseline-full/declared-graph.json").read_text(encoding="utf-8")), "MAKE_DATABASE"),
                    repo_url, base, configuration_id, manifest),
            publish(out, baseline_job, "findings.json", "ERROR_REPORT", base_report,
                    repo_url, base, configuration_id, manifest),
        ]
        target_records = [
            publish(out, target_job, "actual.json", "ACTUAL_GRAPH",
                    graph(repo_url, target, configuration_id, target_job, "ACTUAL_GRAPH",
                          [{"target": t, "dependency": d} for t, deps in incremental["actual"].items() for d in deps],
                          "STATIC_INFERENCE"),
                    repo_url, target, configuration_id, manifest),
            publish(out, target_job, "declared.json", "DECLARED_GRAPH",
                    graph(repo_url, target, configuration_id, target_job, "DECLARED_GRAPH", target_declared, "MAKE_DATABASE"),
                    repo_url, target, configuration_id, manifest),
            publish(out, target_job, "findings.json", "ERROR_REPORT", target_report,
                    repo_url, target, configuration_id, manifest),
            publish(out, target_job, "md.json", "ERROR_REPORT", md_report,
                    repo_url, target, configuration_id, manifest),
        ]
        previous = {f["finding_id"] for f in base_report["findings"]}
        current = {f["finding_id"] for f in target_report["findings"]}
        handoff = {"status": "SUCCEEDED", "profile": incremental["profile"],
                   "repository_url": repo_url, "base_commit": base, "target_commit": target,
                   "configuration_id": configuration_id,
                   "baseline": {"job_id": baseline_job, "actual_graph_uri": base_records[0]["uri"],
                                "error_report_uri": base_records[2]["uri"]},
                   "incremental": {"job_id": target_job, "artifacts": target_records[:3],
                                   "findings_delta": {"added": sorted(current - previous),
                                                      "removed": sorted(previous - current)},
                                   "refreshed": incremental["refreshed"], "reused": incremental["reused"]},
                   "md_report_uri": target_records[3]["uri"], "comparison": equal,
                   "contract_status": "REPORT_READY_GRAPH_SOURCE_BLOCKED"}
        save(out / "manifest.json", {"schema_version": "1.0", "artifacts": manifest})
        save(out / "handoff.json", handoff)
        verify_bundle(out)
        return handoff
    except Exception:
        save(out / "failure.json", {"status": "FAILED", "reason": sys.exc_info()[1].__str__()})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--repository-url", required=True)
    parser.add_argument("--configuration-id", required=True)
    parser.add_argument("--project-path", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.repo.resolve(), args.base, args.target, args.out.resolve(),
                         args.repository_url, args.configuration_id, args.project_path), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
