# ADR：课程示例项目的 E11–E12 图、报告与补丁闭环

- 日期：2026-11-17
- 状态：已采用，用于 A14/B14 课程示例项目
- 范围：C0/C1、同一 B14 DRAFT 镜像、E2 1.0 文件式交接

## 背景

E11 要把 BuildChecker 的真实全量图接入 EChecker 历史状态，E12 要把 A14 实际 MD 报告交给 B14 MDFixer，并对候选补丁动态复验。论文的图与课程 E2 1.0 内容 Schema 存在来源枚举差异；B14 独立服务的 Job、trace、补丁 URI 和配置也必须跨组一致。

## 决策

1. 用 C0 干净构建的 strace 与 GNU Make 数据库建立实际图和声明图，将实际图投影到 EChecker 历史缓存；C1 增量发现与目标全量结果比较。保留原始 trace、数据库、图和哈希，增量实现明确标为教学范围。
2. 向 MDFixer 交付目标 C1 的 1.0 MD-only `Report` 与真实图原件。只对报告做旧版内容 Schema 校验；真实图和重检保留实际 `source`，用文件与 SHA-256 交接，不虚构 `MANUAL_FIXTURE`。
3. 以 B14 原始镜像 ID 和同一配置 ID 锁定执行环境；Git、strace、三项 libunwind 仅只读挂载。复验从干净 C1 Git 快照应用已核对 SHA-256 的补丁，分别记录构建、运行、动态重检与退出码。
4. `patch_uri` 绑定生产 Job。B14 修复 trace 后创建新 Job 时，虽然补丁字节未变，A14 仍对新 URI 重新运行复验。保留旧 Job 的原始记录，最终只接受新 Job 五阶段同一 trace 的 API 回执。
5. 本次按组内明确范围只交付仓库内课程示例项目；不将它称为独立外部项目。

## 结果与限制

新正式 Job `job-d44bbceb4e8a45d4ac1f1b09b370513e` 五阶段均 `SUCCEEDED`，公共 trace 一致；A14 动态重检 `remaining_missing=0`、输出 `12`，B14 最终 `accepted=true`。证据见[正式验收核验](../../../E12_B14_trace正式验收核验_20261117.md)。

BuildChecker 基线使用实际系统调用证据；EChecker 增量仍是 `gcc -MM` 加保守签名的受限教学实现，不包含论文的增量系统调用图归并或多项目性能结论。旧 1.0 Schema 的来源枚举差异保持公开记录，双方未静默更改契约。
