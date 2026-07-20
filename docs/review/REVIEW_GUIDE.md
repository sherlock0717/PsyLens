# 人工复核指南（REVIEW_GUIDE）

> 面向后续真实人工复核者。说明如何使用复核队列、如何记录复核事件、以及复核与离线规则基线提案的边界。

## 1. 复核对象与队列

复核队列 `data/v2/review_queue.csv` 收纳全部待复核项：

- 695 条 legacy 迁移证据（`legacy_ai_label_unreviewed`）；
- 279 条 B 站候选单元 / 离线规则基线提案（`rule_based_proposed_unreviewed`）；
- 2 条歧义证据（`pending_human_resolution`）；
- 后续结构化洞察与行动建议审核项。

字段：`queue_item_id, entity_type, entity_id, source_sample_id, current_status, priority, notes`。

## 2. 复核流程

1. 从 `review_queue.csv` 取一项；
2. 对照 `MECHANISM_CODEBOOK.md` 与 `SURFACE_TOPIC_CODEBOOK.md` 判断；
3. 在 `human_review_log.csv` 记录一条复核事件（见下）；
4. 更新对应实体的 `review_status`。

## 3. 复核记录（human_review_log.csv）

每条复核事件必须记录：

`review_event_id, entity_type, entity_id, source_sample_id, original_label, proposed_label, final_label, reviewer_type, review_status, decision_reason, reviewed_at, notes`

- 真实人工复核时 `reviewer_type = human`；
- 系统迁移事件 `reviewer_type = system_migration`；
- **当前无任何人工复核**：该文件仅含表头或 system_migration 事件。

## 4. 复核与离线规则基线提案的边界

- 离线规则基线提案（`rule_based_proposed_unreviewed`）由本地关键词规则依据 codebook 生成，是**初步提案**，既不是人工复核结论，也不是模型语义判断；
- 只有真实人工在 `human_review_log.csv` 记录后，标签才可标为 `human_reviewed`；
- 页面与文档中，未经人工复核的内容一律标注「草稿 / 规则基线 / 历史观察」，不得写「已人工复核 / 已验证 / 可直接采信」。

## 5. 复核优先级建议

1. 页面拟展示的证据链示例；
2. 支撑草稿洞察的高频证据；
3. B 站 `include_as_evidence=uncertain` 的规则基线提案；
4. 2 条歧义证据；
5. 其余 legacy 与 B 站提案。
