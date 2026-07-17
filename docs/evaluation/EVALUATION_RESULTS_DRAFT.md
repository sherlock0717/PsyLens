# 评测结果草稿（EVALUATION_RESULTS_DRAFT）

> 由 `tools/evaluate_v2.py` 离线、确定性生成，数值来自 `data/v2/evaluation_report.json`。
> 本文件为**草稿**：C/D 组（洞察/建议前置质量）随草稿洞察与建议生成后更新。

## 总体

- `evaluation_status = PASS`（0 阻断，1 警告）。
- 警告项：`parent_semantic_linkage_rate = 0.0`（legacy 历史证据链错位，已知问题）。

## A 数据完整性

| 指标 | 值 | 判定 | 普通语言 |
| --- | --- | --- | --- |
| sample_id_unique_rate | 1.0 | pass | 每条反馈都有唯一编号 |
| evidence_id_unique_rate | 1.0 | pass | 每条证据都有唯一编号 |
| parent_reference_exists_rate | 1.0 | pass | 每条迁移证据都引用了存在的父样本编号 |
| parent_semantic_linkage_rate | 0.0 | warn | legacy 证据能否直接回到声明原话（历史遗留，v2 已用 unit_text 重建关联） |
| evidence_text_match_rate | 1.0 | pass | 每条展示证据都能回到对应的原始反馈 |
| source_url_coverage | 1.0 | pass | 每条反馈底层都能追到原帖（页面不展示 URL） |
| platform_sample_coverage | 3 | pass | 覆盖三个平台 |

## B 编码质量

| 指标 | 值 | 判定 | 普通语言 |
| --- | --- | --- | --- |
| label_completion_rate | 1.0 | pass | provisional 证据都带机制标签（含 uncertain） |
| uncertain_rate | 0.52 | pass | 约一半证据机制暂判不准（诚实标注，不强行归类） |
| invalid_label_rate | 0.0 | pass | 没有规范外标签 |
| evidence_phrase_match_rate | 0.999 | pass | 标注依据短语几乎都能在证据文本中找到 |
| agent_proposal_coverage | 1.0 | pass | B 站候选都给了机器提案 |
| human_review_coverage | 0.0 | warn | 尚无真人复核（当前为 Agent 提案 + legacy 标签） |

## C / D 组

- 洞察前置质量、建议前置质量：随 `structured_insights_draft.jsonl` 与 `public_action_hypotheses_draft.json` 生成后更新（见 `insight_evaluation.json` / `action_evaluation.json`）。

## E 运行质量

| 指标 | 值 | 判定 |
| --- | --- | --- |
| parse_success_rate | 1.0 | pass |
| output_hash_match_rate | 1.0 | pass |
| manifest_completeness | 1.0 | — |

## 口径

- 上述"可回溯/可定位"仅指文本定位，不等于采集/来源/标签/人工复核真实性；
- 机制层约一半为 `uncertain`，说明当前编码保持诚实、未强行归类；
- 人工复核覆盖为 0，公开表述不得写"已人工复核/已验证"。
