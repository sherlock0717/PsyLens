# Prompt 模板：产品假设生成

> 状态：公开重构模板，用于定义外部 provider 的输入输出契约。

## 目标

从证据充分、范围清晰的结构化观察中生成待验证产品假设。每条假设必须能回到观察与证据。

## 指令模板

```text
基于下面的结构化观察，提出一个待验证产品假设。请提供：

1. target_users：目标用户与场景；
2. intervention：干预内容；
3. expected_effect：预期变化；
4. validation_method：访谈、问卷、行为日志、A/B 测试或其他验证方法；
5. success_metric：可衡量的主要指标；
6. guardrail_metrics：防止副作用的护栏指标；
7. source_insight_ids 与 source_evidence_ids；
8. risk：抽样、编码来源、执行成本和因果解释风险。

输出 JSON：
{
  "summary": "...",
  "target_users": "...",
  "intervention": "...",
  "expected_effect": "...",
  "validation_method": "...",
  "success_metric": "...",
  "guardrail_metrics": ["..."],
  "source_insight_ids": ["..."],
  "source_evidence_ids": ["..."],
  "risk": "..."
}

结构化观察：{{insight}}
```

## 约束

- 使用“待验证产品假设”口吻；
- 不把描述性分布直接写成产品因果关系；
- 目标、干预、主要指标和观察窗口需要具体；
- 反馈数量下降必须结合活跃、完成率或留存等护栏指标，避免把沉默误判为改善；
- 缺少来源证据或验证方法时，不生成实施建议。
