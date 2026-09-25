# 论文到 A14 服务的映射

## BuildChecker → FULL_CHECK

依据：*Detecting Build Dependency Errors by Dynamic Analysis of Build Execution against Declaration*（TSE 2025）。

BuildChecker 在 clean build 中跟踪 GNU Make 创建新文件时的读写关系，得到实际依赖；同时读取 GNU Make 内部数据库，得到解析后的声明依赖。对同一 target：

- actual 中存在、declared 中不存在：MISSING；
- declared 中存在、actual 中不存在：REDUNDANT。

课程接口将这两个图和发现报告作为 URI 产物输出。BuildChecker 依赖成功构建，不负责诊断普通编译失败。

## EChecker → INCREMENTAL_CHECK

依据：*Detecting Build Dependency Errors in Incremental Builds*（ISSTA 2024）。

EChecker 复用 clean build 的历史实际依赖图，监控增量构建，并分析 commit 中预处理指令、文件和 Makefile 构建命令的变化，推断新的实际依赖图。没有历史基线时必须先执行 clean build。

课程接口使用 `base_commit` 和 baseline URI 表达历史状态；`findings_delta` 是课程为跨服务消费增加的协议输出。历史构建命令快照在 1.0 中由 A14 内部持久化，公开字段留待 E3 评估。

## DRAFT → A14 环境输入

依据：*Automatic Dockerfile Generation with Large Language Models*（ICSE 2026）。

DRAFT 根据项目上下文、构建错误和候选选择迭代生成 Dockerfile。A14 不把“生成了 Dockerfile”直接视为成功，必须同时检查镜像/元数据、build 和 verify 结果，以及生产任务标识。

## MDFixer ← A14 MD 报告

依据：*Automatic Fixing of Missing Dependency Errors*（ASE 2025）。

MDFixer 根据声明风格修复 Makefile，只消费 MISSING。A14 因此发布 MD-only 报告，并在候选 patch 上重新检测。完整 RD 信息仍保留在 A14 的原始报告中。

## E2 与论文复现的区别

E2 只固化接口、样例、产物形状、来源与验证方法。样例中的 `MANUAL_FIXTURE` 不能冒充论文算法运行结果。算法实现、真实项目、容器权限、性能数据和检测准确性属于 E3。
