# ADR-003：可验证产物与 MD-only 修复交接

- 日期：2026-09-25
- 状态：接受

## Context

依赖图、报告和日志可能较大，不适合全部嵌入 Job。MDFixer 只修复 Missing Dependency，而 A14 的完整报告还可能包含 Redundant Dependency。若不绑定生产来源、版本和配置，B14 可能把错误报告用于错误提交或候选 patch。

## Decision

- Job 通过 URI 引用产物；Artifact 元数据记录 type、producer_job_id、repository、commit、configuration_id、media_type 和 sha256。
- E2 使用 manifest 将 `artifact://` 精确映射到仓库内文件，并拒绝未知 URI、路径越界和 hash 不一致。
- A14 保留完整 findings 报告，同时发布非空 MD-only 报告供 REPAIR 使用。
- 候选 patch 的重检结果必须绑定 patch_uri；B14 汇总最终接受/拒绝决定。

## Alternatives

- 把所有图和日志嵌入 Job：对象过大且内容重复。
- 将完整 MD/RD 报告直接交给 MDFixer：会让修复器接收不支持的 RD。
- 只给 URI 不提供解析和 hash：E2 无法证明产物可读取或未被替换。

## Consequences

E2 可离线验证产物交接；E3 仍需确定真实 registry/对象存储、认证和下载协议。过滤 MD-only 报告时必须保留 finding_id 与生产来源。
