# 草稿结构化洞察报告（STRUCTURED_INSIGHTS_DRAFT_REPORT）

> 由 `tools/build_draft_insights.py` 离线、确定性生成，数值来自 `data/v2/insight_evaluation.json`。
> 统一命名「**结构化洞察**」。**禁用** validated insights / 已验证洞察 / 可直接采信。
> 全部为草稿：`author_type=agent_compiled`、`review_status=agent_compiled_draft`、`publication_status=hidden_pending_review`，默认不公开（见 D-005）。

## 1. 总量

| 项 | 值 |
| --- | --- |
| 结构化洞察总数 | 28 |
| 高支持（≥5 条证据） | 11 |
| 低支持（<5 条证据） | 17 |
| source_evidence_ids 可解析率 | 1.0（全部引用存在于 provisional 证据） |
| 单平台洞察 | 12（占 42.9%，均已标注 single_platform） |

## 2. 生成规则与边界

- 按 (surface_topic, mechanism_label) 聚合 provisional 证据（仅 `analysis_inclusion_status=included`，**不含** uncertain flagged、**不含** 2 条歧义）。
- 至少 5 条证据 → 高支持；否则标 low_support。
- 单平台洞察在 statement 中明确写「仅由单一平台证据支撑，不代表跨平台共识」。
- 每条洞察均写 `limitations`：标签未经人工复核、机制为共现统计而非因果、uncertain 未纳入。
- **不把相关性表述为因果**；**不把置信度当证据强度**；**不隐藏 uncertain**。

## 3. 与 legacy 的关系

- 原 `docs/files/04_validated_insights.jsonl` 保持不变，作为 legacy 中间产物。
- 本草稿基于 v2 provisional 证据重建，命名与口径全部更新为「结构化洞察 / 草稿」。

## 4. 发布状态

- 全部 `hidden_pending_review`，页面默认不展示（D-005 安全默认 `show_draft_v2_insights=false`）。
- 页面可展示的是「历史分析观察」「当前评测状态」「证据链案例」「Demo 运行结果」。
