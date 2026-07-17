# 最终主张审计（FINAL_CLAIM_AUDIT）

> 核查页面与文档不含过强主张，未经记录的人工复核表述已清除。

## 禁用表述核查（页面 + 公开文档）

| 表述 | 结果 |
| --- | --- |
| 可以直接采信 | 无（`test_no_overclaim`） |
| 已验证洞察 / validated insights | 无（统一改为"结构化洞察 / 草稿"） |
| 数据真实 / 数据真实性 | 无（改为"证据文本可在公开样本中定位"） |
| AI 已证明 | 无 |
| 验证完成 | 无 |
| 经人工复核（无日志） | 无（页面 `test_no_overclaim` 断言；`human_review_coverage=0` 如实说明） |
| 三平台机制一致（无完整证据） | 无（单平台洞察均标注 single_platform） |

## 口径

- Agent 提案与人工复核严格区分（`REVIEW_STATUS_DEFINITIONS.md`）；
- 草稿洞察/建议标 `agent_compiled_draft` / `hidden_pending_review`；
- 相关性不表述为因果；置信度不当作证据强度。

## 结论

页面与公开文档主张与实际数据一致，无过强或不实表述。
