# 最终发布审计（FINAL_RELEASE_AUDIT）

> 汇总数据、工程、页面、文档四方面的最终核查。发布状态受延期决策约束。

## 数据

| 项 | 值 |
| --- | --- |
| 样本数 | 360（每平台 120） |
| 迁移证据（legacy 唯一命中） | 695 |
| B 站候选 / Agent 提案 | 279 / 279 |
| provisional 证据 | 927（included 764 + uncertain flagged 163） |
| 三平台覆盖（provisional） | NGA 394 / Tieba 301 / Bili 232 |
| unresolved 歧义 | 2（pending） |
| review status | legacy_ai_label_unreviewed 695；agent_proposed_unreviewed 232；无 human |
| uncertain 比例（provisional 机制层） | ≈0.52 |
| ID 唯一 / 语义定位 | sample/evidence ID 唯一；evidence_text_match_rate=1.0 |
| 所有 insight / action 引用 | 全部可解析（support_resolution_rate=1.0） |

## 工程

- pytest：**77 passed**；compileall：通过；
- 审计退出码：legacy=1 / v2=0 / both=1；
- evaluate_v2：PASS（1 legacy 警告）；
- Demo：确定性，manifest 哈希一致；
- CI workflow（Ubuntu+Windows）与 Pages workflow 已准备；
- 输出保护：运行不改动 `docs/files`、`data/v2`（git diff 干净）；
- 跨平台命令：Python 标准库，Windows/Ubuntu 均可。

## 页面

- 无 Gate / ENTER / 滚动锁 / Claim Ladder / 能力映射 / 招聘链接；
- Hero 保留，品牌视觉保留；
- 工程字段移入 README；页面数字数据驱动（showcase.json）；
- 无 source_url；无完整数据下载入口；无过强主张；
- 单一 h1；footer 含 All rights reserved；关键文档链接有效；
- 响应式（768/390）、skip-link、heading 层级、reduced-motion；JS 失败核心内容仍可读。

## 文档

- README 重写（评测工作流）；Codebook / Pipeline / Demo / 评测方法齐全；
- 统一项目说明底稿已生成（正式 DOCX 待 D-009）；
- 决策包与最终隐私审计齐全；All rights reserved。

## 结论

- legacy_status = BLOCKED；v2_migration_status = PASS；provisional_evidence_status = PASS；
- human_review_status = NOT_STARTED；
- publication_readiness = **PENDING_USER_DECISIONS**（草稿默认隐藏、歧义未定案、无人工复核）。
