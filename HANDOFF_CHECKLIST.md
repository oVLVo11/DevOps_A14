# A14 E2 成果交接检查表

## 已完成材料

- [x] README 与 A14 E2 交付说明
- [x] A14 对 B14 的接口确认
- [x] 统一 JSON Schema 与 API 说明
- [x] FULL_CHECK / INCREMENTAL_CHECK 请求、受理和结果样例
- [x] 合法与非法样例
- [x] actual、declared、完整 findings、MD-only 人工产物
- [x] artifact manifest 与 SHA-256
- [x] 离线校验器
- [x] Backlog、ADR、论文映射、AI 使用记录
- [x] 实际贡献记录：刘威独立完成并使用 AI 辅助
- [x] 最终成果 ZIP 已生成并重新解压验证

## 交接前确认

- [x] 刘威确认 `docs/contributions.md` 与实际情况一致
- [x] 检查 Git 变更范围，确保不包含 `.git` 以外的缓存或临时文件
- [x] 刘威将本次 E2 成果 commit 到 A14 仓库，并在交接消息中记录完整 commit SHA
- [x] 刘威将该 commit push 到 `https://github.com/oVLVo11/DevOps_A14.git`
- [x] 在 GitHub 上确认目标 commit 和交付文件可见
- [ ] 将 A14 仓库地址、commit SHA、成果 ZIP 和验证记录交给课程提交负责人
- [x] A14 对 B14 的接口确认回复已发送，B14 已记录并复核
- [x] B14 已正式发布完整 E2 契约，修复后固定版本为 `ef50c0f6a64ce74d6f2cca5a9b968aedbb0b5856`
- [x] B14 固定 commit 的产物换行符/摘要复现问题已修复并由 A14 复核通过

## A14 不负责的事项

- Moodle 操作；
- 课程平台最终提交；
- E3 真实项目构建与联调。

## 仓库发布说明

- Git commit、push 和 A14 仓库版本发布由刘威负责；
- A14 仓库发布完成后，以 GitHub `main` 可见的完整 commit SHA 作为正式版本标识；
- A14 已通过 `.gitattributes` 禁止 Git 改写产物字节，避免 commit 后 manifest 摘要失效；
- commit SHA 只标识已经提交的仓库快照。将该 SHA 写入 Moodle 或其他说明不会改变它；只有产生新 commit 才会得到新的 SHA。

## 禁止声称

- 已部署真实 HTTP API；
- 已完成真实 Docker 镜像构建；
- 已运行 BuildChecker/EChecker 论文算法；
- 已完成 E3 跨组联调；
- 人工 fixture 是真实检测结果。
