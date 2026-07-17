# Prompt 参考：建议生成（action_generation）

> 仅供真实 provider 参考；Demo 默认 mock 不使用。

任务：把高支持结构化洞察转化为"待验证产品假设"。

要求：
- 统一称"待验证产品假设"，禁用"应该立即实施"；
- 每条必须能回到 source_insight_ids 与 source_evidence_ids；
- 每条包含 expected_effect、validation_method、可衡量 success_metric、risk；
- 明确样本非随机、标签未人工复核。

输出：产品假设 JSON（字段见 data/v2/public_action_hypotheses_draft.json）。
