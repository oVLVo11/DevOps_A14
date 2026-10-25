# DevOps A14 · E2–E7 阶段成果

A14 负责论文项目 BuildChecker 与 EChecker，对应统一任务模型中的 `FULL_CHECK` 和 `INCREMENTAL_CHECK`。配对组 B14 负责 DRAFT 与 MDFixer，对应 `DRAFT` 和 `REPAIR`。

本仓库交付E2接口契约、E3并行测试基线、E4可重复工程环境，以及E5–E7的A组教学范围检测器、原始取证、故障门禁与GitHub CI配置。E5–E7代码覆盖单个GNU Make进程和每项构建任务只有一个最终输出的样例；EChecker跨提交增量检测、真实HTTP服务与跨组联调仍属于后续阶段。

A14 负责将本组成果 commit 并 push 到 A14 GitHub 仓库；A14 不负责在 Moodle 上传压缩包或完成课程平台最终提交。

## 仓库与协作基线

- A14 仓库：`https://github.com/oVLVo11/DevOps_A14.git`
- B14 仓库：`https://github.com/dInG-yAnWen/DevOPs.git`
- B14 E2 1.0 固定基线：`ef50c0f6a64ce74d6f2cca5a9b968aedbb0b5856`（`fix(e2): preserve artifact bytes across Git exports`）
- 该基线继承最初的 E2 发布提交 `689539119e60afd4b224d3163d1ba292992baa95`，只补充 Git 产物字节保护及验证记录；Schema、接口字段、manifest 摘要和产物内容未修改。
- `schema_version`：`1.0`

## 交付入口

- [A14 E5–E7 执行与交付](docs/A14_E5_E7_执行与交付.md)
- [A14 E5–E7 实验报告](docs/A14_E5_E7_实验报告.md)
- [A14 E5–E7 验收记录](docs/A14_E5_E7_验收记录.csv)
- [A14 E4可重复工程环境](e4/README.md)
- [A14 E4交付说明](e4/A14_E4交付说明.md)
- [A14 E4服务器验证记录](e4/验证记录_20261008.md)
- [A14 E3测试基线](e3/README.md)
- [A14 E3交付说明](e3/A14_E3交付说明.md)
- [A14 E3验证记录](e3/验证记录_20261008.md)
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

E3需要Linux、GNU Make、C编译器、Python 3.10或更高版本和`strace`，不需要网络：

```sh
python3 e3/scripts/run_a14_e3.py --run-id my-a14-e3-run
python3 e3/scripts/verify_evidence.py e3/evidence/my-a14-e3-run
```

E4需要课程分配的Ubuntu服务器与Docker。每名操作者只设置仓库级Git身份，然后执行：

```sh
git config --local user.name 241880223
git config --local user.email 1211667299@qq.com
make all
```

已提交的E4服务器证据可离线复核：

```sh
python3 e4/scripts/verify_evidence.py e4/evidence/20261008-a14-e4
python3 e4/scripts/verify_member_evidence.py e4/evidence/20261008-a14-e4-member-241880230
```

## 阶段边界

E2样例中的`example.invalid`、重复数字提交SHA、重复字母镜像digest、日志和检测报告均为`MANUAL_FIXTURE`。E3的命令与程序输出来自真实Linux执行，但`oracle.json`仍是人工答案。E4的`smoke`只验证容器内工具链和跟踪链路。E5–E7必须使用本组提交的源码在课程Linux服务器上生成新证据；仓库中的课程参考材料和Windows本地测试不代替本组云端运行或GitHub检查记录。
