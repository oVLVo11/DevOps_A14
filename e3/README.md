# A14 E3 并行测试基线

A14在E3负责为BuildChecker和EChecker准备可重复、可判断对错的测试输入。本目录交付MD/RD故障项目、C0/C1/C2真实Git版本、人工预期、Linux实际运行日志和一键复现脚本。

E3不声称已经实现BuildChecker或EChecker检测算法。人工答案标记为`INSTRUCTOR_ORACLE`；实际日志只证明样例行为和环境可用。算法实现分别属于后续BuildChecker/EChecker里程碑，跨组真实数据联调属于E12。

## 交付入口

| 路径 | 内容 |
| --- | --- |
| [`A14_E3交付说明.md`](A14_E3交付说明.md) | 需求对照、版本、证据和边界 |
| [`baseline.json`](baseline.json) | C0/C1/C2标签、完整SHA、环境配置和预期输出 |
| [`oracle.json`](oracle.json) | MD/RD及三个版本的人工预期 |
| [`fixtures/md-rd/`](fixtures/md-rd/README.md) | 同时含一条MD和一条RD的故障项目 |
| [`fixtures/commits/project/`](fixtures/commits/project/README.md) | 当前C2快照；历史版本由Git标签读取 |
| [`scripts/run_a14_e3.py`](scripts/run_a14_e3.py) | 一键真实运行，每次创建独立证据目录 |
| [`scripts/verify_evidence.py`](scripts/verify_evidence.py) | 检查摘要、命令日志、观察和Git版本关系 |
| [`evidence/20261008-a14-e3/`](evidence/20261008-a14-e3/observations.json) | WSL2/Linux真实运行证据，8/8通过 |
| [`验证记录_20261008.md`](验证记录_20261008.md) | 人类可读的执行与结果摘要 |

## C0/C1/C2

| 版本 | 标签 | 完整commit SHA | 预期 |
| --- | --- | --- | --- |
| C0 | `a14-e3-c0` | `4445e4be50af6683b75017e7fa65c4f8212ea80e` | 声明正确，clean输出10 |
| C1 | `a14-e3-c1` | `37fcadb1eced8d2504b1d5e0bd96f3b8091568b1` | 新增`feature.h`但漏声明，clean输出12 |
| C2 | `a14-e3-c2` | `59a3ce2b47461505143d020703e81bd8f68dd667` | 只增加`-DMODE=7`；继承C1产物时输出12，clean输出19 |

## 一键复现

需要Linux、Git、GNU Make、C编译器、Python 3.10或更高版本和`strace`，不需要网络：

```sh
git clone https://github.com/oVLVo11/DevOps_A14.git
cd DevOps_A14
python3 e3/scripts/run_a14_e3.py --run-id my-a14-e3-run
python3 e3/scripts/verify_evidence.py e3/evidence/my-a14-e3-run
```

脚本从三个固定commit执行`git archive`，不会切换或修改当前分支。生成目录`e3/evidence/<run-id>/`；若run-id已存在会拒绝覆盖。临时构建位于已忽略的`e3/work/<run-id>/`。

## 已观察行为

| 场景 | 实际观察 | 结论 |
| --- | --- | --- |
| MD初始构建 | make退出0，程序输出1 | 构建成功不代表声明正确 |
| 修改`config.h` | 增量输出1，clean输出2 | 缺失依赖造成旧产物 |
| 修改`unused.h` | 再次出现编译和链接命令 | 冗余声明造成多余构建 |
| 删除`config.h` | make退出2 | 失败日志可定位到固定样例 |
| C0 | clean输出10 | 可作为正确历史基线 |
| C1修改`feature.h` | 增量输出12，clean输出15 | 新增头文件依赖未声明 |
| C1到C2 | 增量输出12，clean输出19 | 普通时间戳检查没有识别命令变化 |
| Linux原始跟踪 | strace退出0并记录`config.h`访问 | 原始访问证据可供后续构图使用 |

## 与B14的关系

B14独立准备DRAFT和MDFixer基线。E3双方可以并行完成，不把B14人工MD报告冒充A14检测结果；真实数据接入与修复闭环留到E12。
