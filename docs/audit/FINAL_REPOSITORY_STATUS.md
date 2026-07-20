# 最终仓库状态（FINAL_REPOSITORY_STATUS）

```
engineering_completion   = COMPLETE_LOCALLY
remote_ci_status         = NOT_VERIFIED
public_release_readiness = PENDING_USER_DECISIONS
main_merge_status        = NOT_STARTED
pages_deployment_status  = NOT_STARTED
```

> 说明：本地全部测试通过（113 passed）、Ruff 阻断级无告警、评测/公开数据/showcase/Demo 均可确定性运行。
> 由于本地环境无 GitHub CLI 与网络凭据，远程 Ubuntu/Windows CI 结论无法在此直接确认（推送会触发 CI）。
> 因此按「远程 CI 未验证」口径记为 `COMPLETE_LOCALLY`，不写作 `COMPLETE`。

## 发布前修正达成情况（PSYLENS-FINAL-CORRECTIONS-001）

1. public 数据不含 source_url —— 完成（`data/public/**`）；
2. 规则基线命名完成 —— 完成（`rule_based_*`，无 `agent_proposed`）；
3. evaluator 指标真实计算 —— 完成（8 项真实分子/分母，四分状态）；
4. showcase 无硬编码关键数字 —— 完成（全部计算，篡改测试保障）；
5. pipeline 模板与依赖补齐 —— 完成（`pipeline/**`，reconstructed_template）；
6. 正式 DOCX 已生成 —— 完成（`docs/files/PsyLens_project_brief.docx`）；
7. 本地全部测试通过 —— 完成（113 passed）；
8. 远程 CI —— **NOT_VERIFIED**（见上）；
9. main 未修改 —— 保持；
10. Pages 未部署 —— 保持。

## 分层状态

| 维度 | 状态 |
| --- | --- |
| legacy_status | BLOCKED |
| v2_migration_status | PASS |
| provisional_evidence_status | PASS |
| human_review_status | NOT_STARTED |
| publication_readiness | PENDING_USER_DECISIONS |

## 交付清单

- 数据：`data/v2/**`（迁移、规则基线提案、provisional、评测、复核队列、决策登记）；
- 公开数据：`data/public/**`（脱敏、无来源链接）+ `data/internal_manifest/RESTRICTED_DATA_FILES.md`；
- 工具：`tools/`（审计、v2 生成、复核基础设施、provisional、评测、洞察、建议、Demo、页面数据、公开数据、DOCX）；
- 评测：`evaluation/`（指标/阈值/失败类型）；
- Demo：`demo/`（离线可运行 + 测试）；
- 采集分析：`pipeline/**`（发现模板、配置、Prompt、示例、依赖）；
- 文档：`docs/methodology`、`docs/review`、`docs/evaluation`、`docs/pipeline`、`docs/phase1`、`docs/audit`、`docs/decisions`；
- 正式说明：`docs/files/PsyLens_project_brief.docx`（旧 v3/v4 归档至 `archive/project_brief_legacy/`）；
- 页面：`docs/index.html` + `docs/style.css` + `docs/assets/data/showcase.json`（数据驱动）；
- CI：`.github/workflows/ci.yml`、`pages.yml`；
- 许可：`RIGHTS_AND_USAGE.md`（All rights reserved）。

## 待用户决策

见 `docs/decisions/FINAL_DECISION_PACKET.md`（D-001 ~ D-010）。在决策前不合并 main、不改线上 Pages、不冒充正式发布、不公开争议下载入口。
