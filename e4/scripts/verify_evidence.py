#!/usr/bin/env python3
"""离线校验 A14 E4 服务器证据。"""

import argparse
import hashlib
import json
import re
from pathlib import Path


def require(condition, message):
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_checksums(directory):
    checksum_file = directory / "SHA256SUMS.txt"
    require(checksum_file.is_file(), f"缺少 {checksum_file}")
    count = 0
    for line in checksum_file.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        require(match is not None, f"摘要行格式错误：{line}")
        relative = match.group(2).removeprefix("./")
        target = directory / relative
        require(target.is_file(), f"摘要目标不存在：{target}")
        require(sha256(target) == match.group(1), f"摘要不匹配：{target}")
        count += 1
    return count


def verify_run(run_dir, expected_sha):
    required = {
        "build.log",
        "compose-config.yaml",
        "env.json",
        "env-permissions.txt",
        "git-status.txt",
        "image.json",
        "image-runtime.json",
        "secret-scan.txt",
        "smoke.json",
        "source-sha.txt",
        "test.log",
        "toolchain.lock",
        "tracked-env.txt",
    }
    for name in required:
        require((run_dir / name).is_file(), f"{run_dir.name} 缺少 {name}")

    source_sha = (run_dir / "source-sha.txt").read_text(encoding="utf-8").strip()
    require(re.fullmatch(r"[0-9a-f]{40}", source_sha) is not None, "源码 SHA 格式错误")
    require(source_sha == expected_sha, f"{run_dir.name} 源码 SHA 不一致")

    environment = json.loads((run_dir / "env.json").read_text(encoding="utf-8"))
    require(environment["problems"] == [], f"{run_dir.name} 环境存在必需项问题")
    require(environment["os"] == "Ubuntu 22.04.5 LTS", f"{run_dir.name} 系统版本异常")
    require(environment["arch"] == "x86_64", f"{run_dir.name} 宿主架构异常")
    require(environment["git"]["user.name"] == "241880223", f"{run_dir.name} Git 身份异常")

    image = json.loads((run_dir / "image.json").read_text(encoding="utf-8"))
    require(image["image"] == "e4-buildchecker:241880223", f"{run_dir.name} 镜像名异常")
    require(re.fullmatch(r"sha256:[0-9a-f]{64}", image["id"]) is not None, "镜像 ID 格式错误")
    require(image["arch"] == "amd64", f"{run_dir.name} 镜像架构异常")

    runtime = json.loads((run_dir / "image-runtime.json").read_text(encoding="utf-8"))
    require(runtime == {"user": "app", "architecture": "amd64", "os": "linux"}, "镜像运行身份异常")

    test_log = (run_dir / "test.log").read_text(encoding="utf-8")
    require("collected 3 items" in test_log and "3 passed" in test_log, f"{run_dir.name} 单测未通过")

    smoke = json.loads((run_dir / "smoke.json").read_text(encoding="utf-8"))
    require(smoke["passed"] is True, f"{run_dir.name} 冒烟结果未通过")
    require(smoke["make_exit_code"] == 0, f"{run_dir.name} make 退出码异常")
    require(smoke["app_output"] == "1", f"{run_dir.name} 程序输出异常")
    require(smoke["config_h_opened"], f"{run_dir.name} 未跟踪到 config.h")
    require(smoke["unused_h_opened"] == [], f"{run_dir.name} 意外跟踪到 unused.h")

    secret_scan = (run_dir / "secret-scan.txt").read_text(encoding="utf-8")
    require("密钥检查：未发现问题" in secret_scan, f"{run_dir.name} 密钥扫描未通过")
    require((run_dir / "env-permissions.txt").read_text(encoding="utf-8") == "600 .env\n", "env 权限异常")
    require((run_dir / "tracked-env.txt").read_bytes() == b"", f"{run_dir.name} .env 被跟踪")
    require((run_dir / "git-status.txt").read_text(encoding="utf-8") == "## main...origin/main\n", "Git 状态异常")

    compose = (run_dir / "compose-config.yaml").read_text(encoding="utf-8")
    for fragment in ("network_mode: none", "cpus: 2", "mem_limit: \"1073741824\"", "pids_limit: 256", "SYS_PTRACE", "no-new-privileges:true"):
        require(fragment in compose, f"{run_dir.name} Compose 缺少 {fragment}")

    toolchain = (run_dir / "toolchain.lock").read_bytes()
    return {"image_id": image["id"], "trace_lines": smoke["trace_lines"], "toolchain": toolchain}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument(
        "--expected-sha",
        default="0a23b30d5c1e6eef118ce8d422c4a5b0444215f5",
    )
    args = parser.parse_args()
    evidence = args.evidence.resolve()

    root_count = verify_checksums(evidence)
    run1_count = verify_checksums(evidence / "run-1")
    run2_count = verify_checksums(evidence / "run-2")
    first = verify_run(evidence / "run-1", args.expected_sha)
    second = verify_run(evidence / "run-2", args.expected_sha)
    require(first["toolchain"] == second["toolchain"], "两次工具链清单不同")
    require((evidence / "toolchain.diff").read_bytes() == b"", "工具链 diff 非空")

    negative = (evidence / "secret-scan-negative.txt").read_text(encoding="utf-8")
    clean = (evidence / "secret-scan-clean.txt").read_text(encoding="utf-8")
    require("FOUND" in negative and "发现 2 处疑似泄露" in negative, "假 Key 未被检出")
    require("sk-d***" in negative, "扫描日志没有保留掩码后的假 Key 标记")
    require("密钥检查：未发现问题" in clean, "清理后复扫未通过")

    troubleshooting = evidence / "troubleshooting"
    require("deb.debian.org" in (troubleshooting / "01-official-debian-source-stall.log").read_text(encoding="utf-8"), "缺少官方源停滞日志")
    require("ModuleNotFoundError" in (troubleshooting / "03-pytest-console-entry-failure.log").read_text(encoding="utf-8"), "缺少 pytest 失败日志")

    files = sum(1 for path in evidence.rglob("*") if path.is_file())
    print(
        "PASS: "
        f"evidence_files={files}, root_checksums={root_count}, "
        f"run_checksums={run1_count + run2_count}, runs=2, "
        f"toolchain_equal=true, image_ids_equal={str(first['image_id'] == second['image_id']).lower()}"
    )


if __name__ == "__main__":
    main()
