# 评测结果草稿（EVALUATION_RESULTS_DRAFT）

> 由 `tools/evaluate_v2.py` 离线、确定性生成，数值来自 `data/v2/evaluation_report.json`。
> 每个指标均记录 value / numerator / denominator / status / plain_explanation，为真实计算结果。

## 总体状态（四分）

| 状态 | 值 | 含义 |
| --- | --- | --- |
| structural_integrity_status | PASS | 编号、证据文本回溯、编码规范、manifest、哈希、可重复性均通过 |
| label_review_status | NOT_STARTED | 尚无真人复核（human_review_log.csv 无 reviewer_type=human） |
| insight_draft_status | DRAFT | 结构化洞察为草稿，默认不公开 |
| release_readiness_status | PENDING_REVIEW | 草稿隐藏、歧义未定案、无人工复核，发布待复核 |

不再输出单一裸露的 `evaluation_status=PASS`。

## A 数据完整性

| 指标 | 值 | 判定 | 普通语言 |
| --- | --- | --- | --- |
| sample_id_unique_rate | 1.0 | pass | 每条反馈都有唯一编号 |
| evidence_id_unique_rate | 1.0 | pass | 每条证据都有唯一编号 |
| parent_reference_exists_rate | 1.0 | pass | 每条证据都指向一个真实存在的原始反馈 |
| evidence_text_match_rate | 1.0 | pass | 每条展示证据都能回到对应的原始反馈 |
| source_url_coverage | 1.0 | pass | 仅内部来源字段非空率，不代表可追溯真实性；公开层不含该字段 |
| platform_sample_coverage | 3 | pass | 覆盖三个平台 |

> 已移除误导性的 `parent_semantic_linkage_rate`（legacy 派生、恒为 0）；证据回溯以 `parent_reference_exists_rate` 与 `evidence_text_match_rate` 表达。

## B 编码质量

| 指标 | 值 | 判定 | 普通语言 |
| --- | --- | --- | --- |
| label_completion_rate | 1.0 | pass | provisional 证据都带机制标签（含 uncertain） |
| uncertain_rate | 0.52 | pass | 约一半证据机制暂判不准（诚实标注，不强行归类） |
| invalid_label_rate | 0.0 | pass | 没有规范外标签 |
| evidence_phrase_match_rate | 0.999 | pass | 标注依据短语几乎都能在证据文本中找到 |
| rule_based_proposal_coverage | 1.0 | pass | B 站候选都给出了离线规则基线提案 |
| human_review_coverage | 0.0 | not_started | 尚无真人复核（当前为规则基线提案 + legacy 标签） |
| human_override_rate | n/a | n/a | 无人工复核时不适用（不写作 0.0） |

## C 洞察前置质量

| 指标 | 值 | 判定 |
| --- | --- | --- |
| support_resolution_rate | 1.0 | pass |
| platform_coverage（平均平台数/洞察） | 1.75 | pass |
| time_window_coverage（平均时间窗/洞察） | 1.54 | pass |
| low_support_claim_rate | 0.61 | warn |
| single_platform_claim_rate | 0.43 | pass |

## D 建议前置质量

| 指标 | 值 | 判定 |
| --- | --- | --- |
| action_to_insight_linkage_rate | 1.0 | pass |
| action_to_evidence_linkage_rate | 1.0 | pass |
| validation_plan_coverage | 1.0 | pass |
| expected_effect_coverage | 1.0 | pass |

## E 运行质量

| 指标 | 值 | 判定 |
| --- | --- | --- |
| parse_success_rate | 1.0 | pass |
| stage_completion_rate | 1.0 | pass |
| repeatability_rate | 1.0 | pass |
| manifest_completeness | 1.0 | pass |
| output_hash_match_rate | 1.0 | pass |

> `stage_completion_rate` 依据计划阶段与实际产物存在状态计算；`repeatability_rate` 在临时目录重复运行 provisional 生成流程并比较产物哈希；均非写死。

## 口径

- 上述"可回溯/可定位"仅指文本定位，不等于采集/来源/标签/人工复核真实性；
- 机制层约一半为 `uncertain`，说明当前编码保持诚实、未强行归类；
- 人工复核覆盖为 0，公开表述不得写"已人工复核/已验证"。
