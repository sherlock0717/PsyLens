# 最终发布审计（FINAL_RELEASE_AUDIT）

> 汇总数据、工程、页面、文档四方面的最终核查。发布状态受延期决策约束；远程 CI 见文末。

## 数据

| 项 | 值 |
| --- | --- |
| 样本数 | 360（每平台 120） |
| 迁移证据（legacy 唯一命中） | 695 |
| B 站候选 / 离线规则基线提案 | 279 / 279 |
| provisional 证据 | 927（included 764 + uncertain flagged 163） |
| 三平台覆盖（provisional） | NGA 394 / Tieba 301 / Bili 232 |
| unresolved 歧义 | 2（pending） |
| review status | legacy_ai_label_unreviewed 695；rule_based_proposed_unreviewed 232；无 human |
| uncertain 比例（provisional 机制层） | ≈0.52 |
| ID 唯一 / 文本定位 | sample/evidence ID 唯一；evidence_text_match_rate=1.0 |
| 公开数据副本 | `data/public/`（无 source_url，SHA-256 记录于 public_manifest） |

## 工程

- pytest：**113 passed**；compileall：通过；Ruff：无忽略、无告警（阻断级启用）；
- 评测器：`--input-dir`/`--output-dir` 真实生效；8 项指标真实计算，记录分子/分母；
  状态四分：structural_integrity=PASS、label_review=NOT_STARTED、insight_draft=DRAFT、release_readiness=PENDING_REVIEW；
- showcase：全部计数与状态由数据文件计算（无硬编码），`--repo-ref` 生成文档链接；
- 公开数据：`build_public_dataset.py` 生成脱敏副本；
- Demo：确定性、离线 mock；
- 正式 DOCX：`docs/files/PsyLens_project_brief.docx` 已生成、可读，v3/v4 归档至 `archive/project_brief_legacy/`；
- 输出保护：运行不改动 `docs/files`、`data/v2`（git diff 干净）。

## 页面

- 无 Gate / 能力映射 / 招聘链接 / 内部阻断术语（P0/P1/BLOCKED/裸露 PASS）；
- Hero 保留；状态用自然语言（结构校验/待人工复核/规则基线）；
- 数字数据驱动（showcase.json）；`textContent`/`createElement` 渲染，无 innerHTML 注入；
- 无 source_url；无完整数据下载入口；文档链接由 repo_ref 生成，含正式 DOCX。

## 文档

- README 重写（评测工作流，无内部阻断说明）；Codebook / Pipeline / Demo / 评测方法齐全；
- pipeline 模板（发现/配置/Prompt/示例/依赖）补齐，历史不可精确复现处标 `reconstructed_template`；
- 正式项目说明 DOCX 已生成；决策包与隐私审计更新；All rights reserved。

## 结论

- structural_integrity_status = PASS；label_review_status = NOT_STARTED；insight_draft_status = DRAFT；
- provisional_evidence_status = PASS；publication_readiness = PENDING_USER_DECISIONS；
- remote_ci_status = **NOT_VERIFIED**（本地环境无 GitHub CLI/网络凭据，无法直接确认 Actions 运行；推送会触发 CI，需线上查看结论）。
