# E11–E12 PR 技术验收记录

- PR：[A14 #8](https://github.com/oVLVo11/DevOps_A14/pull/8)。个人分支 `student/241880223/e11-e12`，基线为尚待组内审核的 E8–E10 [#7](https://github.com/oVLVo11/DevOps_A14/pull/7) 分支。
- 范围：按组内本次决定，仅以 `e3/fixtures/commits/project` 课程示例完成 A/B 联调；未执行独立外部项目接入。个人报告、ADR、AI 使用记录均位于本目录。
- 代码审查准备：相对上游 E8–E10 分支核对新增文件与 `git diff --check`，没有空白错误。E11 A 的五项测试、旧版 E2 69 项契约测试及跨组原件均有运行证据。
- 跨组验收：B14 新正式 Job `job-d44bbceb4e8a45d4ac1f1b09b370513e` 五阶段与总结果均 `SUCCEEDED`，同一公共 trace；A14 动态复验 Job `job-40dbc3ab56db472d865791c73051dc19` 输出 `12`、剩余 MISSING `0`。A14 新复验 ZIP 的 46 项文件、B14 最终回执 ZIP 的 24 项文件均已按哈希核验；见[最终回执记录](../../../E12_B14_trace正式验收核验_20261117.md)。

## 本轮 CI 实测

个人报告提交 `5a2ba5c55c4c9f4ebdb2f023726b0fcbe698beda` 的三个 PR 工作流均为 `success`：

| 工作流 | GitHub Actions |
| --- | --- |
| E11 A integration | [44075361627](https://github.com/oVLVo11/DevOps_A14/actions/runs/44075361627) |
| E8–E10 teaching validation | [44075361621](https://github.com/oVLVo11/DevOps_A14/actions/runs/44075361621) |
| E7 A quality gate | [44075361615](https://github.com/oVLVo11/DevOps_A14/actions/runs/44075361615) |

本记录自身提交后应以 PR 页面显示的最新 head 与检查状态为最终 CI 依据，不能将旧提交的成功误写为新提交的成功。

后续提交 `73dc5c33d45edef23dac7dace69452a9f10cf23a` 的三项工作流也全部为 `success`：[E11 A](https://github.com/oVLVo11/DevOps_A14/actions/runs/44076545541)、[E8–E10](https://github.com/oVLVo11/DevOps_A14/actions/runs/44076545580)、[E7](https://github.com/oVLVo11/DevOps_A14/actions/runs/44076545560)。

## 在线 PR 状态与剩余动作

本轮最初核验时，#8 为草稿且描述仍停留在早期联调。GitHub 连接器写入返回 403、浏览器未登录；随后通过本机已有 GitHub 授权更新了 #8 描述，内容指向个人报告与正式最终回执，并将 #8 转为待审。再次查询确认 `draft=false`、`mergeable=true`、当前仍无组内 review、尚未合并。#7 也尚未合并；应由组内成员审核 #7、#8，再依课程安排合并。AI 自检和 CI 成功不能代替组内 review。

当前 PR 描述已指向本目录的个人报告、ADR、AI 记录，以及 `handoff/e12/` 中新 URI 复验、B14 正式最终回执等证据；说明课程示例范围、共同 trace、`source` 的 1.0 契约边界和论文教学实现边界。
