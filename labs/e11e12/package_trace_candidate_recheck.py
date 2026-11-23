"""Verify B14's formal trace candidate and package A14's new dynamic recheck."""

import argparse
import hashlib
import json
import tarfile
import zipfile
from pathlib import Path

from package_handoff import package


TRACE = "trace-3ccaf76e466544e9b78f08a0ddffea67"
CONFIGURATION = "386d1bf4dad4c495b810636f4192e5154f50be512c63a0ce7179447d3f9927bc"
C0 = "4445e4be50af6683b75017e7fa65c4f8212ea80e"
C1 = "37fcadb1eced8d2504b1d5e0bd96f3b8091568b1"
IMAGE = "sha256:4131a5fadae383e2e0b5c5ea76caa76314833c3195a67058d036df6d85b5ffa4"
PATCH_SHA = "0606c04039cefa3648c0cc4a39d5ebecf7b4b367fdf664dfefc771840f665323"
MD_SHA = "2aead6b279506a1c689873a1d660e2f8902f4dc11ee3fdcf9b3b170c4be64ea5"
B14_JOB = "job-d44bbceb4e8a45d4ac1f1b09b370513e"
PATCH_URI = f"artifact://b14-repair/{B14_JOB}/candidate.patch"
SOURCE = "evidence/formal-recheck-trace-fix-02/"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load_json(data):
    return json.loads(data.decode("utf-8"))


def save_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def put(folder, name, data):
    path = folder / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--b14", type=Path, required=True)
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--folder", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    args = parser.parse_args()
    if args.folder.exists():
        raise ValueError("Output folder already exists")

    b14_archive_sha = sha(args.b14.read_bytes())
    raw_archive_sha = sha(args.raw.read_bytes())
    with zipfile.ZipFile(args.b14) as incoming, tarfile.open(args.raw, "r:gz") as raw:
        zip_names = incoming.namelist()
        if len(zip_names) != len(set(zip_names)) or any(
            name.startswith("/") or "\\" in name or ".." in Path(name).parts
            for name in zip_names
        ):
            raise ValueError("Unsafe B14 ZIP entries")
        checksum_lines = incoming.read("SHA256SUMS.txt").decode("utf-8").splitlines()
        if len(checksum_lines) != len(zip_names) - 1:
            raise ValueError("B14 checksum count differs from ZIP entries")
        for line in checksum_lines:
            expected, name = line.split("  ", 1)
            if name not in zip_names or sha(incoming.read(name)) != expected:
                raise ValueError("B14 checksum mismatch: " + name)
        members = {member.name: member for member in raw.getmembers()}
        if len(members) != len(raw.getmembers()) or any(
            name.startswith("/") or ".." in Path(name).parts or not (member.isfile() or member.isdir())
            for name, member in members.items()
        ):
            raise ValueError("Unsafe raw archive members")

        def raw_bytes(name):
            member = members.get(name)
            if member is None or not member.isfile():
                raise ValueError("Missing raw evidence: " + name)
            return raw.extractfile(member).read()

        handoff = load_json(incoming.read("handoff.json"))
        submit = load_json(incoming.read("submit.json"))
        state = load_json(incoming.read("receipt/job-state.json"))
        repair = load_json(incoming.read("receipt/repair.json"))
        candidate = load_json(incoming.read("candidate-manifest.json"))
        patch = incoming.read("candidate.patch")
        md = incoming.read("md-only.json")
        if submit["input"]["handoff_sha256"] != sha(incoming.read("handoff.json")):
            raise ValueError("B14 submit/handoff hash mismatch")
        if handoff["recheck_file"] != "recheck-return.json":
            raise ValueError("Unexpected B14 recheck return filename")
        if state["job_id"] != B14_JOB or state["status"] != "RUNNING":
            raise ValueError("Unexpected B14 job state")
        if sha(patch) != PATCH_SHA or sha(md) != MD_SHA:
            raise ValueError("B14 patch or MD report changed")
        if patch != incoming.read("receipt/candidate.patch") or md != incoming.read("receipt/md-only.json"):
            raise ValueError("B14 candidate copies differ")
        if patch != raw_bytes("trace-fix-02/candidate.patch"):
            raise ValueError("Executed patch differs from B14 candidate")
        if candidate["artifact"]["uri"] != PATCH_URI or candidate["artifact"]["sha256"] != PATCH_SHA:
            raise ValueError("B14 candidate manifest differs")
        if repair["data"]["patch"]["uri"] != PATCH_URI or repair["trace_id"] != TRACE:
            raise ValueError("B14 repair stage differs")
        for name in ("draft", "full-check", "incremental-check", "repair"):
            envelope = load_json(incoming.read(f"receipt/{name}.json"))
            if (envelope["job_id"], envelope["trace_id"], envelope["status"]) != (B14_JOB, TRACE, "SUCCEEDED"):
                raise ValueError("B14 stage identity differs: " + name)
        result = load_json(raw_bytes(SOURCE + "recheck.json"))
        findings = load_json(raw_bytes(SOURCE + "full-recheck/findings.json"))
        exit_codes = load_json(raw_bytes("trace-fix-02/acceptance-exit-codes.json"))
        if (result["patch_uri"], result["patch_sha256"], result["configuration_id"],
            result["repository"]["commit"], result["source"], result["status"],
            result["remaining_missing"], result["test_output"]) != (
                PATCH_URI, PATCH_SHA, CONFIGURATION, C1, "DYNAMIC_TRACE", "SUCCEEDED", 0, "12"):
            raise ValueError("A14 recheck result differs")
        if findings["status"] != "SUCCEEDED" or findings["findings"] or findings["build_exit_code"] != 0:
            raise ValueError("A14 dynamic findings differ")
        if exit_codes != {"clean_exit_code": 0, "build_exit_code": 0, "verify_exit_code": 0}:
            raise ValueError("A14 acceptance exit codes differ")
        if raw_bytes("trace-fix-02/acceptance-verify.log") != b"12\n":
            raise ValueError("A14 acceptance output differs")
        if raw_bytes("trace-fix-02/container-exit.txt") != b"0\n" or raw_bytes("trace-fix-02/acceptance-container-exit.txt") != b"0\n":
            raise ValueError("A14 container failed")
        traces = sorted(name for name, member in members.items() if name.startswith(SOURCE + "full-recheck/trace/t.") and member.isfile())
        if not traces:
            raise ValueError("Missing dynamic trace originals")

        folder = args.folder
        folder.mkdir(parents=True)
        direct = {
            "candidate.patch": "trace-fix-02/candidate.patch",
            "recheck.json": SOURCE + "recheck.json",
            "recheck-return.json": SOURCE + "recheck.json",
            "clean.log": SOURCE + "clean.log",
            "build.log": SOURCE + "build.log",
            "verify.log": SOURCE + "verify.log",
            "patch-check.log": SOURCE + "patch-check.log",
            "patch-apply.log": SOURCE + "patch-apply.log",
            "recheck-run.log": "trace-fix-02/recheck-run.log",
            "recheck-container-exit.txt": "trace-fix-02/container-exit.txt",
            "acceptance/clean.log": "trace-fix-02/acceptance-clean.log",
            "acceptance/build.log": "trace-fix-02/acceptance-build.log",
            "acceptance/verify.log": "trace-fix-02/acceptance-verify.log",
            "acceptance/exit-codes.json": "trace-fix-02/acceptance-exit-codes.json",
            "acceptance/container-exit.txt": "trace-fix-02/acceptance-container-exit.txt",
            "tool-mounts.sha256": "evidence/tool-mounts.sha256",
            "toolchain.txt": "evidence/toolchain.txt",
        }
        for destination, source in direct.items():
            put(folder, destination, raw_bytes(source))
        put(folder, "input-md.json", md)
        put(folder, "b14/candidate-manifest.json", incoming.read("candidate-manifest.json"))
        put(folder, "b14/repair.json", incoming.read("receipt/repair.json"))
        put(folder, "b14/job-state.json", incoming.read("receipt/job-state.json"))
        for name, member in members.items():
            if name.startswith(SOURCE + "full-recheck/") and member.isfile():
                put(folder, name.removeprefix(SOURCE), raw_bytes(name))

    session = {
        "schema": "a14-e12-trace-candidate-recheck-handoff-1",
        "status": "SUCCEEDED",
        "trace_id": TRACE,
        "configuration_id": CONFIGURATION,
        "repository_url": "https://github.com/oVLVo11/DevOps_A14.git",
        "base_commit": C0,
        "target_commit": C1,
        "b14_repair_job_id": B14_JOB,
        "b14_service_commit": "e7b8de36f4a800c403b991ed816e93a2f02e52ba",
        "patch_uri": PATCH_URI,
        "patch_sha256": PATCH_SHA,
        "input_md_uri": "artifact://a14-check/job-22c9005a7b0e42f9bdc48078420a9d91/md.json",
        "input_md_sha256": MD_SHA,
        "image_id": IMAGE,
        "recheck_job_id": result["producer_job_id"],
        "dynamic_trace_id": findings["trace_id"],
        "source": result["source"],
        "remaining_missing": result["remaining_missing"],
        "test_output": result["test_output"],
        "execution": {
            "environment": "A14 course Linux server, B14 original image.tar already loaded",
            "network": "none",
            "additional_tools": "Same read-only Git, strace and three libunwind mounts as C0/C1 detection",
            "tool_mount_hashes": "tool-mounts.sha256",
            "recheck_container_exit_code": 0,
            "clean_build_container_exit_code": 0,
            **exit_codes,
        },
        "b14_candidate_archive_sha256": b14_archive_sha,
        "server_raw_archive_sha256": raw_archive_sha,
    }
    save_json(args.folder / "session.json", session)
    (args.folder / "README.md").write_text(
        "# A14 → B14：trace 修复后正式 Job 的动态复验\n\n"
        f"本包对应 B14 正常创建的 Job `{B14_JOB}`，补丁 URI `{PATCH_URI}`。"
        "`recheck-return.json` 与原始 `recheck.json` 逐字节相同，可复制到 B14 交接文件指定的位置。\n\n"
        "A14 在课程 Linux 服务器的原 B14 镜像中，使用与 C0/C1 检测相同的五项只读工具挂载，"
        "从干净 C1 Git 快照应用补丁。补丁 SHA-256、输入 MD 报告、五阶段公共 trace、配置 ID 和镜像 ID 均已核对。"
        "动态重检来源为 `DYNAMIC_TRACE`，剩余 MISSING=0；独立 `make clean && make && ./app` 的退出码均为 0，输出 12。\n\n"
        "`SHA256SUMS.txt` 可逐项校验；`manifest.json` 包含全部文件哈希。"
        "`full-recheck/trace/t.*` 是未改写的进程 trace 原件。"
        "`session.json` 锁定本轮 Job、补丁、C1、配置与镜像身份。"
        "B14 可据此完成 recheck 阶段并出具最终 API 回执。\n",
        encoding="utf-8",
    )
    files = sorted(path for path in args.folder.rglob("*") if path.is_file())
    manifest = {
        "schema": "a14-e12-trace-candidate-recheck-manifest-1",
        "trace_id": TRACE,
        "configuration_id": CONFIGURATION,
        "image_id": IMAGE,
        "target_commit": C1,
        "b14_repair_job_id": B14_JOB,
        "patch_uri": PATCH_URI,
        "patch_sha256": PATCH_SHA,
        "recheck_job_id": result["producer_job_id"],
        "build_exit_code": 0,
        "verify_exit_code": 0,
        "remaining_missing": 0,
        "source": "DYNAMIC_TRACE",
        "files": [{"path": p.relative_to(args.folder).as_posix(), "sha256": sha(p.read_bytes())} for p in files],
    }
    save_json(args.folder / "manifest.json", manifest)
    print(json.dumps(package(args.folder, args.archive), ensure_ascii=False))


if __name__ == "__main__":
    main()
