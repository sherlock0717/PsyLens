# B 站证据处理队列指南（BILI_EVIDENCE_QUEUE_GUIDE）

> B 站 120 条样本在 legacy 证据层无确定覆盖（Phase 0：证据实际只来自 NGA+Tieba）。
> 本阶段只做**确定性候选切分**，生成待处理队列，**不生成最终机制标签、不调用模型**。

## 1. 队列文件

`data/v2/bili_evidence_queue.csv`，字段：

`queue_id, sample_id, legacy_clean_id, raw_text, candidate_unit_index, candidate_unit_text, split_method, surface_topic_candidate, mechanism_label_candidate, candidate_status, human_review_status, notes`

## 2. 切分规则（split_method）

- 按 **句号、问号、感叹号、分号、换行**（中英文：`。！？；` 与 `.!?;` 及 `\n`）切分；
- **过短语气词不单独作为候选**：最小单元长度 `min_len = 6`（字符）；
- 切分方式在 `split_method` 字段中可解释地记录。

## 3. 字段约束（本阶段强制）

- `surface_topic_candidate`：可以为空（不臆测）；
- `mechanism_label_candidate`：必须为空或 `unassigned`（**禁止最终机制标签**）；
- `candidate_status = pending_review`；
- `human_review_status = not_reviewed`。

## 4. 规模

- 覆盖 B 站 **120** 个 sample_id；
- 候选单元 **279** 条（确定性切分结果）。

## 5. 后续处理建议（不在本阶段执行）

1. 人工或模型辅助为候选单元标注 `surface_topic` 与 `mechanism_label`，并建立复核记录；
2. 过滤明显无信息的过短/口水候选；
3. 通过复核的单元并入正式 `evidence_v2`，分配正式 `BILI_xxxx_U0x` 证据 ID；
4. 完成后证据层才覆盖三平台，publication_readiness 方可重新评估。

## 6. 定位口径

- 队列中的 `candidate_unit_text` 由样本 `raw_text` 确定性切分得到，属「候选证据单元」；
- 这**不是**最终证据，也不代表任何机制结论；
- 在人工复核并标注前，不得据此形成三平台机制一致等结论。
