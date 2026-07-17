# 草稿产品假设报告（ACTION_HYPOTHESES_DRAFT_REPORT）

> 由 `tools/build_draft_actions.py` 离线、确定性生成，数值来自 `data/v2/action_evaluation.json`。
> 全部为「**待验证产品假设**」草稿：`author_type=agent_compiled`、`review_status=agent_compiled_draft`、`publication_status=hidden_pending_review`，默认不公开（见 D-006）。

## 1. legacy 身份说明

- `docs/files/05_action_matrix.json` 保持不变，明确为 **legacy AI 中间产物**（纯 AI 生成、无可追溯字段）。
- 本草稿基于高支持结构化洞察重建，具备完整可追溯字段。

## 2. 总量与可追溯性

| 项 | 值 |
| --- | --- |
| 草稿产品假设数 | 6 |
| action_to_insight_linkage_rate | 1.0（每条都能回到具体洞察） |
| action_to_evidence_linkage_rate | 1.0（每条都能回到具体证据） |
| validation_plan_coverage | 1.0（每条都有验证方法） |
| expected_effect_coverage | 1.0（每条都有预期效果） |
| human_curated_rate | 0.0（未人工整理） |

## 3. 字段与规则

每条含：`action_id, title, summary, source_insight_ids, source_evidence_ids, evidence_summary, expected_effect, validation_method, success_metric, risk, priority_basis, author_type, review_status, publication_status`。

- **不使用**「应该立即实施」等祈使表述；统一为「待验证产品假设」。
- 每条 `risk` 明确：样本为公开社区反馈、非随机抽样；标签未人工复核；结论为草稿假设。
- 优先级依据 `priority_basis` = 支撑证据数 + 单/多平台。

## 4. 发布状态

- 全部 `hidden_pending_review`，页面默认不展示（D-006 安全默认 `show_draft_action_hypotheses=false`）。
