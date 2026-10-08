# 输入材料与版本来源

## A14 仓库

- URL：`https://github.com/oVLVo11/DevOps_A14.git`
- 检查日期：2026-09-25
- 初始状态：检查时远程为空仓库
- 发布状态：E2 材料由刘威 commit 并 push 到 A14 GitHub `main`；完整 commit SHA 在交接消息中提供

## B14 仓库

- URL：`https://github.com/dInG-yAnWen/DevOPs.git`
- 检查日期：2026-09-25
- E2 1.0 固定基线：`ef50c0f6a64ce74d6f2cca5a9b968aedbb0b5856`
- 基线提交标题：`fix(e2): preserve artifact bytes across Git exports`
- 原始 E2 发布提交：`689539119e60afd4b224d3163d1ba292992baa95`（存在 Git 换行规范化导致的产物摘要复现问题，已由新基线修复）
- 说明：修复提交增加 `/contracts/artifacts/** -text` 和验证记录；Schema、接口字段、manifest 摘要值及产物原始内容均未修改。
- A14 复核：从新基线执行 Git 原始导出后，19 份产物摘要一致，解压后的 69 项检查全部通过。

## B14 协作包

- 文件：`DevOPs.zip`
- SHA-256：`1858D6521DBF4A6AC75A6FD55CB2B32FAC77A812D09D28190FFF262AD2715448`
- 内容：统一 Schema、API 说明、四类任务样例、人工产物、manifest、校验器、Backlog 与 ADR
- 使用方式：A14 采用其中的 1.0 契约作为协作基线，并新增 A14 责任说明和验收记录
- 发布对应：B14 完整 E2 契约及字节一致性修复对应 `ef50c0f6a64ce74d6f2cca5a9b968aedbb0b5856`

## 课程材料

- `E2_需求与接口契约_20260910.pptx`：E2 范围、四服务协作、统一 Job、状态、错误、产物、校验和过程材料要求
- `E3_并行测试基线_20260910.pptx`：E3 MD/RD样例、C0/C1/C2、命令、日志、人工预期与Linux原始跟踪要求
- `E4/E4_20260929.pptx`：E4可重复工程环境、容器、依赖固定、测试、密钥与重跑验收要求
- `E4/E4_A组全流程命令手册_20260929.md`：A组服务器连接、仓库初始化、`make all`、证据核对与E5接续说明
- `E4/E4实验包/A-buildchecker`：A14 E4 BuildChecker服务骨架与官方样例
- `A14_协作确认消息.md`：B14 向 A14 提出的 DRAFT 契约与资料请求

## 论文材料

- `_TSE__BuildChecker.pdf`
- `_ISSTA_2024__Detecting_Build_Dependency_Error.pdf`
- `_ICSE_2026__Dockerfile_auto_generation.pdf`
- `_ASE_2025__Auto_fix_missing_dependency_errors.pdf`

论文只作为系统职责、输入输出和算法边界依据。本 E2 包不声称复现实验指标。

## E3样例与执行来源

- 初始MD/RD源码结构参考本地课程`E4实验包/A-buildchecker/fixtures/md-rd`，纳入A14后新增独立README、人工答案、连续提交项目、运行脚本和证据校验。
- C0/C1/C2均为A14仓库真实提交：`4445e4be50af6683b75017e7fa65c4f8212ea80e`、`37fcadb1eced8d2504b1d5e0bd96f3b8091568b1`、`59a3ce2b47461505143d020703e81bd8f68dd667`。
- 正式E3证据在WSL2 Linux上于2026-10-08实际运行生成；环境和命令分别记录在`e3/evidence/20261008-a14-e3/environment.json`和`commands.json`。
- B14截至复核时远程`main`为`eb2c62c9a3222cbcb25a8bc204348ce91b3c9ba8`，其DRAFT/MDFixer E3基线独立存在；A14没有复制其结果充当本组证据。

## E4模板来源与边界

- E4根目录的`Dockerfile`、Compose、Makefile、依赖锁、BuildChecker骨架、测试、服务器自检和密钥扫描以课程`A-buildchecker`模板为基线，整合进既有A14仓库时保留E2/E3内容。
- B组实验包只用于核对职责边界；A14没有复制DRAFT服务、Docker客户端或`docker.sock`配置。
- E4正式运行证据只能由课程分配的Ubuntu服务器生成。未获得服务器访问并完成两次重跑前，不把本地文件检查记作E4完成证据。
- A14课程ECS在容器构建中访问`deb.debian.org`连续两次停滞；`mirrors.aliyun.com`的Debian主源与安全源经同一服务器实际访问返回成功，因此E4 Dockerfile显式使用该镜像源，apt签名校验保持启用。
- 课程ECS镜像中直接执行pytest控制台入口无法导入`/app/buildchecker`，而`python3 -m pytest`在同一镜像中通过三项测试；Makefile据此使用模块方式启动固定版本的pytest。
