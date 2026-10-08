# 241880230 E4 复现证据导入说明

## 证据来源

- 原始包：`241880230-e4-rerun-evidence.tar.gz`
- 原始包 SHA-256：`1ab60a44aa00c5db7d956545f6cc7226602da27e29e1de32982d1caa0b34cca5`
- 服务器运行目录：`/root/241880230-e4-rerun-20261008-130532/buildchecker/work/20261008-130807`
- 被测源码：`0a23b30d5c1e6eef118ce8d422c4a5b0444215f5`

原始压缩包及其外部摘要保存在 A14 交付目录，不把压缩二进制重复提交到 Git。`original-archive.sha256` 保留提交人提供的摘要行，`reproduction-report.txt` 保留原始复现说明。

## 安全导入边界

原始包的 `attempts/01-preflight-sigpipe/run-e4.sh` 包含用于负向扫描的完整假 Key 生成结果。它不是实际凭据，但原样提交会使仓库敏感信息扫描按设计失败。因此 Git 证据目录不导入该脚本，只保留同一失败尝试的 `preflight.log`、`runtime-status.txt` 和 `session.log`。原始脚本仍由外部原始包及其固定 SHA-256 覆盖，没有把失败历史改写成成功记录。

成功运行的日志、环境、镜像、Compose、工具链、测试、smoke、密钥扫描、时间和操作声明均按服务器原始字节导入。仓库 `SHA256SUMS.txt` 是针对这份安全导入副本重新生成的摘要清单。

## 人员与 AI 边界

原始运行记录写明：命令由 Codex 在庄一凡授权下远程执行，当时 `human_confirmation=pending`。该原始声明保持不变。

运行结束后，A14 当前用户于 2026-10-08 在任务对话中提交全部文件并声明“本人已确认”。后续确认单独记录在 `human-confirmation.txt`；不反向修改原始 `operator-attestation.txt`，也不把 Codex 协助执行表述为纯人工键盘操作。
