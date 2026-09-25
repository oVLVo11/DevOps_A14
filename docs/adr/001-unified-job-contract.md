# ADR-001：采用统一异步 Job 契约

- 日期：2026-09-25
- 状态：双方接受；B14 E2 修复后基线已发布为 `ef50c0f6a64ce74d6f2cca5a9b968aedbb0b5856`

## Context

四类任务可能包含构建、分析或修复，执行时间不适合由同步 HTTP 请求持续等待。E2 又不要求部署真实 API，需要先固定可验证的交换对象。

## Decision

采用统一 `Request`、`Accepted`、`Job` 和 `ApiError` 模型。POST 成功受理返回 202 与服务端生成的 job_id；调用方通过 `GET /v1/jobs/{job_id}` 查询。任务状态限定为 QUEUED、RUNNING、SUCCEEDED、FAILED、TIMED_OUT、CANCELLED。

HTTP 状态表达请求是否被接受或查询是否成功；Job status 表达后台执行结果。检测到 MD/RD 属于 FULL_CHECK/INCREMENTAL_CHECK 的正常输出，不把它编码为 FAILED。

## Alternatives

- 同步等待：实现简单，但构建与分析可能超时，调用方也难以查询或恢复。
- 四套完全独立响应：会重复定义状态、错误与追踪字段，跨服务流程难以关联。

## Consequences

E3 需要任务存储、幂等处理、状态迁移和终态锁定。E2 通过 Schema、样例和离线校验固定这些行为，不伪造运行时实现。
