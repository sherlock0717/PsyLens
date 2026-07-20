# Prompt 模板：建议生成（action_generation）

> 状态：`reconstructed_template`。公开模板，不保证与历史运行逐字一致。

## 目标

从高支持结构化洞察生成**待验证产品假设**草稿，每条能回到洞察与证据。

## 指令（模板）

```
基于下面这条结构化洞察，提出一个待验证产品假设。要求：
1. 使用"待验证假设"口吻，不写"应该立即实施"；
2. 给出 expected_effect（预期效果）、validation_method（验证办法）、
   可衡量的 success_metric；
3. 引用 source_insight_ids 与 source_evidence_ids；
4. 标注这是草稿、未经实验验证。
输出 JSON：{ "summary": "...", "expected_effect": "...", "validation_method": "...",
            "success_metric": "...", "source_insight_ids": [...],
            "source_evidence_ids": [...], "risk": "..." }
洞察：{{insight}}
```
