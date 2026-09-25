# DevOps A14 · E2 接口契约交付

A14 负责论文项目 BuildChecker 与 EChecker，对应统一任务模型中的 `FULL_CHECK` 和 `INCREMENTAL_CHECK`。配对组 B14 负责 DRAFT 与 MDFixer，对应 `DRAFT` 和 `REPAIR`。

本仓库交付 E2 接口契约、人工样例、可读取产物、离线校验器和设计过程记录。E2 不部署真实 HTTP API，也不声称已执行真实 Docker 构建、BuildChecker、EChecker 或跨组运行。真实项目、镜像和端到端联调属于 E3。

A14 负责将本组成果 commit 并 push 到 A14 GitHub 仓库；A14 不负责在 Moodle 上传压缩包或完成课程平台最终提交。

## 仓库与协作基线

- A14 仓库：`https://github.com/oVLVo11/DevOps_A14.git`
- B14 仓库：`https://github.com/dInG-yAnWen/DevOPs.git`
- B14 E2 1.0 固定基线：`ef50c0f6a64ce74d6f2cca5a9b968aedbb0b5856`（`fix(e2): preserve artifact bytes across Git exports`）
- 该基线继承最初的 E2 发布提交 `689539119e60afd4b224d3163d1ba292992baa95`，只补充 Git 产物字节保护及验证记录；Schema、接口字段、manifest 摘要和产物内容未修改。
- `schema_version`：`1.0`

## 交付入口

- [A14 E2 交付说明](docs/A14_E2交付说明.md)
- [A14 对 B14 的接口确认](A14_B14_接口确认回复.md)
- [成果交接检查表](HANDOFF_CHECKLIST.md)
- [统一接口说明](contracts/API.md)
- [统一 JSON Schema](contracts/task.schema.json)
- [合法与非法样例](contracts/examples/README.md)
- [产物索引](contracts/artifact-manifest.json)
- [论文到服务映射](docs/paper-mapping.md)
- [Backlog](docs/backlog.md)
- [架构决策](docs/adr/)
- [AI 使用记录](docs/AI_USAGE.md)
- [成员分工](docs/contributions.md)
- [验证记录](docs/validation.md)
- [输入材料与版本来源](docs/source-provenance.md)

## 本地验收

需要 Python 3.10 或更高版本，不需要网络：

```sh
python validator/validate.py --suite
python validator/validate.py contracts/examples/valid/full_result.json
python validator/validate.py contracts/examples/valid/incremental_result.json
python validator/validate.py --read-artifact artifact://a14-check/job-full01/md.json
```

`validator/validate.py` 只验证 JSON、跨字段语义、产物路径和 SHA-256，不执行样例中的命令，不下载镜像，也不调用真实服务。

## E2 边界

样例中的 `example.invalid`、重复数字提交 SHA、重复字母镜像 digest、日志和检测报告均为 `MANUAL_FIXTURE`。它们用于验证协议形状与交接规则，不能作为真实实验结果。E3 再选择真实 Make/C/C++ 项目，运行 DRAFT、BuildChecker、EChecker 和 MDFixer。
