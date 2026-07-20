# Prompt 参考：产品假设生成

> 仅供接入外部 provider 时参考；离线 Demo 使用确定性 mock，不调用本提示词。

任务：将具有明确证据支撑的结构化观察转化为可验证的产品假设。

每条假设需要包含：

- 目标用户与使用场景；
- 干预内容；
- `source_insight_ids` 与 `source_evidence_ids`；
- `expected_effect`；
- `validation_method`；
- 可衡量的 `success_metric`；
- 可能的副作用和停止条件；
- 抽样、编码来源和因果解释限制。

输出使用“待验证产品假设”口吻，不写成确定实施结论。字段契约可参考 `demo/src/pipeline.py` 生成的 `actions.json`。
