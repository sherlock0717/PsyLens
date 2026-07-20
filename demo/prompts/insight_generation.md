# Prompt 参考：洞察生成（insight_generation）

> 仅供真实 provider 参考；Demo 默认 mock 不使用。

任务：把同一 (话题, 机制) 的多条证据聚合为一条结构化洞察。

要求：
- 统一称"结构化洞察"，禁用"已验证洞察/可直接采信"；
- 记录 source_evidence_ids、evidence_count、platform_coverage；
- 单平台必须标明，不表述为跨平台共识；
- 写明 limitations（标签未人工复核、共现非因果、uncertain 未纳入）。

输出：结构化洞察 JSON（字段见 data/v2/structured_insights_draft.jsonl）。
