# A14 E2 / E3 / E4 Backlog

状态说明：DONE_LOCAL表示A14本地材料与校验完成；DONE_CROSS_GROUP表示双方已确认相应协作基线；DONE_REAL表示已经保留真实命令和运行证据。

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
| A14-E3-01 | MD/RD故障项目与人工依据 | 刘威 | 一条MD、一条RD、源码和行为依据可复现 | DONE_REAL |
| A14-E3-02 | C0/C1/C2真实版本 | 刘威 | 三个完整commit SHA和标签存在，配置固定 | DONE_REAL |
| A14-E3-03 | 增量与clean行为对照 | 刘威 | C0=10、C1=12/15、C2=12/19均有日志 | DONE_REAL |
| A14-E3-04 | Linux环境与原始跟踪 | 刘威 | 工具版本、strace、make数据库和失败日志已保存 | DONE_REAL |
| A14-E3-05 | 一键运行与证据校验 | 刘威 | 新run-id不覆盖旧证据，SHA-256和Git版本可验证 | DONE_REAL |
| A14-E3-06 | E3文档、贡献与仓库发布 | 刘威 | README、交付说明、验证记录、贡献与AI记录完整 | DONE |
| A14-E4-01 | BuildChecker服务骨架 | 刘威 | version/smoke CLI、三项单测和E3样例齐全 | DONE_LOCAL |
| A14-E4-02 | 容器与依赖固定 | 刘威 | Dockerfile固定digest、锁文件带哈希、工具链可导出 | DONE_LOCAL |
| A14-E4-03 | Compose与一键命令 | 刘威 | 资源限制、无网络、SYS_PTRACE及make all链路完整 | DONE_LOCAL |
| A14-E4-04 | 密钥隔离与扫描 | 刘威 | .env不入库/镜像，工作区、历史与镜像可扫描 | DONE_LOCAL |
| A14-E4-05 | 课程服务器首次运行 | 刘威 | doctor/build/test/smoke/scan全部通过并保存证据 | DONE_REAL |
| A14-E4-06 | 第二份独立克隆重跑 | 刘威 | 同一SHA重跑，工具链和结论一致或差异有解释 | DONE_REAL_SAME_OPERATOR |
| A14-E4-07 | E4证据发布与交接 | 刘威 | 选择证据、验证摘要、完整SHA与交付包已发布 | DONE |
| A14-LATER-01 | BuildChecker实际图、声明图与自动MD/RD推断 | A14 | 真实检测结果与E3人工答案对照 | DEFERRED_TO_LATER_MILESTONE |
| A14-LATER-02 | EChecker跨提交增量检测 | A14 | 基于C0图检测C1/C2并输出变化 | DEFERRED_TO_LATER_MILESTONE |
| A14-E12-01 | 接入B14真实数据与MDFixer重检闭环 | A14/B14 | 真实DRAFT输入、MD交接、patch重检闭环 | DEFERRED_TO_E12 |

## 未决事项

- A14 不负责 Moodle 或课程平台最终提交；仓库地址、commit SHA 和 ZIP 由课程提交负责人继续使用。
- 后续EChecker实现需决定历史构建命令快照是内部持久化还是升级契约公开`build_commands_uri`。
- E3证据来自WSL2原生Linux进程；容器内系统调用跟踪权限留到后续服务实现阶段确认。
- E4两次服务器运行均由刘威在独立克隆中完成；若教师严格要求不同组员亲自重跑，仍需金凌或庄一凡补充其本人操作证据。
