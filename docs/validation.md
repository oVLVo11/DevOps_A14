# A14 E2 本地验证记录

- 日期：2026-09-25
- 环境：Windows；Codex bundled Python 3.12
- 仓库：`https://github.com/oVLVo11/DevOps_A14.git`
- 状态：E2 成果、本地归档和 Git 发布归档均须通过同一套件；正式版本以 A14 GitHub `main` 的完整 commit SHA 为准

## 验证命令

在仓库根目录执行：

```powershell
python validator/validate.py --suite
python validator/validate.py contracts/examples/valid/full_result.json
python validator/validate.py contracts/examples/valid/incremental_result.json
python validator/validate.py --read-artifact artifact://a14-check/job-full01/md.json
```

## 结果

```text
Schema backend: offline subset (only keywords used by this contract)
PASS: 69 checks (schema=1, artifacts=19, valid=20, invalid=7, mutations=20, resolver=2)
PASS: contracts/examples/valid/full_result.json
PASS: contracts/examples/valid/incremental_result.json
PASS: artifact://a14-check/job-full01/md.json 可读取
```

| 验证层 | 数量 | 结果 |
| --- | ---: | --- |
| Schema 关键字与引用 | 1 | 通过 |
| manifest 产物、路径和 SHA-256 | 19 | 通过 |
| 合法请求、响应和 Job | 20 | 通过 |
| 独立非法样例 | 7 | 全部按预期拒绝 |
| 运行时语义变异 | 20 | 全部按预期拒绝 |
| 未注册 URI 与越界解析 | 2 | 全部按预期拒绝 |

## 关键行为

- 未知 job_type 被拒绝；
- 短 commit SHA 被拒绝；
- INCREMENTAL_CHECK 缺失 baseline 被拒绝；
- baseline 的 repository、commit 或 configuration 不匹配被拒绝；
- REPAIR 收到 REDUNDANT 或版本不匹配报告被拒绝；
- FULL_CHECK 正常发现 MD/RD 仍可为 SUCCEEDED；
- 非零退出码不能标记为 PASSED；
- REPAIR 重检仍有 MD 时不能把候选标记为接受；
- artifact URI、实际文件、SHA-256 和生产元数据一致。

## 校验器边界

离线后端只实现本契约使用到的 JSON Schema Draft 2020-12 关键字，遇到未知关键字会失败。安装 `jsonschema` 后，校验器会优先使用完整后端。

校验器不执行 shell 命令、不检出远程仓库、不拉取镜像、不调用 LLM、不验证真实 HTTP 状态迁移，也不证明 BuildChecker/EChecker 算法正确。这些属于 E3。

## ZIP 复核

最终 ZIP 生成后已解压到临时目录重新运行完整套件，69 项检查再次通过。归档中不包含 `.git`、`__pycache__` 或 `.pyc` 文件；临时复核目录已删除。

## B14 交叉复核反馈

B14 已确认收到 A14 回复，并在其仓库记录交接结果。B14 反馈其校验器已通过 A14 的 20 个合法样例，按预期拒绝 7 个非法样例，并核对 19 份产物；双方 Schema 规则一致。B14 最初指定 E2 1.0 基线为 `689539119e60afd4b224d3163d1ba292992baa95`。

A14 对最初基线执行原始 `git archive` 时发现 Git 换行规范化导致 19 份产物摘要不符。双方随后均通过 `.gitattributes` 对 `contracts/artifacts/**` 设置 `-text`。B14 发布修复基线 `ef50c0f6a64ce74d6f2cca5a9b968aedbb0b5856` 后，A14 已核验：该 commit 存在，修复只增加字节保护及验证记录；从该 commit 原始导出后，19 份产物 SHA-256 全部匹配，69 项契约检查全部通过。该问题已关闭。
