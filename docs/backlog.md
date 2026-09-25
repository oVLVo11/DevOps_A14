# A14 E2 / E3 Backlog

状态说明：DONE_LOCAL 表示 A14 本地材料与校验完成；DONE_CROSS_GROUP 表示 B14 已确认并记录对应 E2 基线；两者都不代表已进入 E3。

| ID | 工作 | 负责人 | 验收条件 | 状态 |
| --- | --- | --- | --- | --- |
| A14-E2-01 | 统一 Job 与错误模型审阅 | 刘威 | 四类任务结构、状态和错误语义明确 | DONE_LOCAL |
| A14-E2-02 | FULL_CHECK 契约与样例 | 刘威 | request/accepted/result 可校验，图与报告可读取 | DONE_LOCAL |
| A14-E2-03 | INCREMENTAL_CHECK 契约与 baseline 约束 | 刘威 | base/current/configuration 不匹配会被拒绝 | DONE_LOCAL |
| A14-E2-04 | MD/RD 与 findings_delta 语义 | 刘威 | 正常发现不误报为 Job 失败 | DONE_LOCAL |
| A14-E2-05 | A14 产物、manifest 与 MD-only 报告 | 刘威 | 文件存在、SHA-256 和生产来源一致 | DONE_LOCAL |
| A14-E2-06 | 最小校验与反例 | 刘威 | 正例通过、反例拒绝、读取命令可复现 | DONE_LOCAL |
| A14-E2-07 | 论文映射、ADR、AI 与交付文档 | 刘威 | 设计依据、决策和限制可追溯 | DONE_LOCAL |
| A14-E2-08 | B14 接口确认 | 刘威 / B14 联系人 | 双方记录同一 schema_version 与正式 commit | DONE_CROSS_GROUP（B14 `ef50c0f6a64ce74d6f2cca5a9b968aedbb0b5856`） |
| A14-E2-09 | 个人贡献与工作证据 | 刘威 | 独立完成及 AI 辅助情况与实际文档证据一致 | DONE_LOCAL |
| A14-E2-10 | A14 仓库发布 | 刘威 | E2 成果已 commit、push，GitHub 可见且完整 SHA 已记录 | DONE |
| A14-E2-11 | E2 成果交接 | 刘威 | 仓库地址、commit SHA、ZIP、验证记录和接口回复交给课程提交负责人 | READY_FOR_HANDOFF |
| A14-E2-12 | Git 产物字节复现 | 刘威 / B14 联系人 | 双方通过 `.gitattributes` 保留产物字节，Git 导出后 19 份摘要一致且 69 项检查通过 | DONE_CROSS_GROUP |
| A14-E3-01 | 选择真实 Make/C/C++ 项目 | A14/B14 | 公开 repo、C0/C1、命令和环境可复现 | DEFERRED_TO_E3 |
| A14-E3-02 | BuildChecker 实现 | A14 | clean build 产生 actual/declared graph 与 MD/RD | DEFERRED_TO_E3 |
| A14-E3-03 | EChecker 实现 | A14 | 基于 C0 baseline 检测 C1 并输出 delta | DEFERRED_TO_E3 |
| A14-E3-04 | DRAFT 环境联调 | A14/B14 | A14 可拉取镜像并读取至少一个真实产物 | DEFERRED_TO_E3 |
| A14-E3-05 | MDFixer 重检闭环 | A14/B14 | patch 绑定基线，build/verify/recheck 均通过 | DEFERRED_TO_E3 |

## 未决事项

- A14 不负责 Moodle 或课程平台最终提交；仓库地址、commit SHA 和 ZIP 由课程提交负责人继续使用。
- E3 决定历史构建命令快照是内部持久化还是升级契约公开 `build_commands_uri`。
- E3 明确容器内系统调用跟踪所需权限和安全策略。
