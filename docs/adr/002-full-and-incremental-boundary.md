# ADR-002：BuildChecker 建立基线，EChecker 更新基线

- 日期：2026-09-25
- 状态：接受

## Context

BuildChecker 通过 clean build 获得完整、低误报的实际依赖图；EChecker 利用历史图和 commit 变化避免每次 clean build。两者场景不同，不能把 INCREMENTAL_CHECK 简化为另一次 FULL_CHECK，也不能在没有可信 baseline 时直接增量推断。

## Decision

- FULL_CHECK 在固定 repo、commit 和 configuration 上产生 actual graph、declared graph 与 ERROR_REPORT。
- INCREMENTAL_CHECK 必须提供不同的 base/current commit，并绑定同仓库、同 configuration 的 baseline actual graph 和报告。
- 影响依赖图的工具链、构建选项或环境变量变化时生成新的 configuration_id，并重新运行 FULL_CHECK。
- EChecker 需要的历史构建命令快照在 1.0 中由 A14 内部保存；公开字段变更留待 E3 双方评审。

## Alternatives

- 每个提交都执行 FULL_CHECK：语义可靠但失去 EChecker 的增量效率目标。
- 没有 baseline 也执行增量检查：无法证明历史图来源和版本匹配。
- A14 单方面增加契约字段：会让 B14 的严格消费者拒绝对象。

## Consequences

调用方必须保存 baseline URI 与 configuration_id。E3 实现需核验提交存在、工作树状态正确，并确保增量构建使用当前源码而不是镜像内旧源码。
