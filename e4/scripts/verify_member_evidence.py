#!/usr/bin/env python3
"""离线校验 241880230 的 A14 E4 独立克隆复现证据。"""

import argparse
import hashlib
import json
import re
from pathlib import Path


EXPECTED_SOURCE = "0a23b30d5c1e6eef118ce8d422c4a5b0444215f5"
EXPECTED_ARCHIVE = "1ab60a44aa00c5db7d956545f6cc7226602da27e29e1de32982d1caa0b34cca5"
EXPECTED_TOOLCHAIN = "bc70f4e9e436d2567c88588171d7fd4575a614c442874baa089407106bbf9358"
REPO = Path(__file__).resolve().parents[2]


def require(condition, message):
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def text(path):
    return path.read_text(encoding="utf-8")


def verify_checksums(directory):
    checksum_file = directory / "SHA256SUMS.txt"
    require(checksum_file.is_file(), "缺少安全导入副本 SHA256SUMS.txt")
    count = 0
    for line in text(checksum_file).splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  \./(.+)", line)
        require(match is not None, f"摘要行格式错误：{line}")
        target = directory / match.group(2)
        require(target.is_file(), f"摘要目标不存在：{target}")
        require(sha256(target) == match.group(1), f"摘要不匹配：{target}")
        count += 1
    return count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    evidence = args.evidence.resolve()

    checksum_count = verify_checksums(evidence)

    source = text(evidence / "source-sha.txt").strip()
    require(source == EXPECTED_SOURCE, "源码 SHA 不一致")

    environment = json.loads(text(evidence / "env.json"))
    require(environment["problems"] == [], "环境存在必需项问题")
    require(environment["os"] == "Ubuntu 22.04.5 LTS", "系统版本异常")
    require(environment["arch"] == "x86_64", "宿主架构异常")
    require(environment["git"] == {"user.name": "241880230", "user.email": "241880230@localhost"}, "Git 身份异常")

    require(text(evidence / "make-all-exit.txt").strip() == "0", "make all 未成功")
    test_log = text(evidence / "test.log")
    require("collected 3 items" in test_log and "3 passed" in test_log, "pytest 未通过")

    smoke = json.loads(text(evidence / "smoke.json"))
    require(smoke["passed"] is True, "smoke 未通过")
    require(smoke["make_exit_code"] == 0, "样例 make 退出码异常")
    require(smoke["app_output"] == "1", "样例输出异常")
    require(smoke["config_h_opened"], "未跟踪到 config.h")
    require(smoke["unused_h_opened"] == [], "意外跟踪到 unused.h")

    image = json.loads(text(evidence / "image.json"))
    require(image["image"] == "e4-buildchecker:241880230", "镜像名异常")
    require(re.fullmatch(r"sha256:[0-9a-f]{64}", image["id"]) is not None, "镜像 ID 格式错误")
    require(image["arch"] == "amd64", "镜像架构异常")
    runtime = json.loads(text(evidence / "image-runtime.json"))
    require(runtime == {"user": "app", "architecture": "amd64", "os": "linux"}, "镜像运行身份异常")

    toolchain = evidence / "toolchain.lock"
    require(sha256(toolchain) == EXPECTED_TOOLCHAIN, "工具链摘要异常")
    reference = REPO / "e4/evidence/20261008-a14-e4/run-1/toolchain.lock"
    require(toolchain.read_bytes() == reference.read_bytes(), "工具链与 A14 首次运行不同")

    require(text(evidence / "env-permissions.txt") == "600 .env\n", ".env 权限异常")
    require((evidence / "tracked-env.txt").read_bytes() == b"", ".env 被 Git 跟踪")
    require(text(evidence / "git-status.txt") == "## HEAD (no branch)\n", "独立克隆 Git 状态异常")

    compose = text(evidence / "compose-config.yaml")
    for fragment in (
        "image: e4-buildchecker:241880230",
        "network_mode: none",
        "cpus: 2",
        'mem_limit: "1073741824"',
        "pids_limit: 256",
        "SYS_PTRACE",
        "no-new-privileges:true",
    ):
        require(fragment in compose, f"Compose 缺少 {fragment}")

    negative = text(evidence / "secret-scan-negative.txt")
    clean = text(evidence / "secret-scan-clean.txt")
    require(text(evidence / "negative-scan-exit.txt").strip() == "negative_scan_exit=1", "负向扫描退出码异常")
    require("FOUND" in negative and "sk-d***" in negative and "发现 1 处疑似泄露" in negative, "假 Key 未被正确检出和掩码")
    require("密钥检查：未发现问题" in clean, "清理后密钥扫描未通过")

    attestation = text(evidence / "operator-attestation.txt")
    require("student_id=241880230" in attestation, "原始操作声明身份异常")
    require("execution_mode=Codex-assisted remote execution" in attestation, "缺少 AI 执行披露")
    require("human_confirmation=pending" in attestation, "原始声明未保持生成时状态")
    confirmation = text(evidence / "human-confirmation.txt")
    require("confirmation_received=yes" in confirmation, "缺少运行后的成员确认")
    require("execution_disclosure=Codex-assisted remote execution authorized by 庄一凡" in confirmation, "确认记录缺少 AI 边界")

    archive_line = text(evidence / "original-archive.sha256").strip()
    require(archive_line == f"{EXPECTED_ARCHIVE}  241880230-e4-rerun-evidence.tar.gz", "原始包摘要记录异常")
    require("证据压缩包 SHA-256：" + EXPECTED_ARCHIVE in text(evidence / "reproduction-report.txt"), "复现说明摘要异常")

    attempt = evidence / "attempts/01-preflight-sigpipe"
    require((attempt / "preflight.log").is_file(), "缺少首次预检失败日志")
    require((attempt / "runtime-status.txt").is_file(), "缺少首次预检状态")
    require(not (attempt / "run-e4.sh").exists(), "安全导入副本不应包含带完整假 Key 的脚本")
    require("run-e4.sh" in text(evidence / "IMPORT_NOTES.md"), "缺少省略原始脚本的解释")

    files = sum(1 for path in evidence.rglob("*") if path.is_file())
    print(
        "PASS: "
        f"member=241880230, evidence_files={files}, checksums={checksum_count}, "
        "source=true, tests=true, smoke=true, toolchain_equal=true, "
        "secret_negative=true, confirmation_received=true"
    )


if __name__ == "__main__":
    main()
