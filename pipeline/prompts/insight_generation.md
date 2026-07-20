# Prompt 模板：洞察生成（insight_generation）

> 状态：`reconstructed_template`。公开模板，不保证与历史运行逐字一致。

## 目标

把同一 (话题 × 机制) 的证据聚合成**结构化洞察草稿**，每条洞察必须回到具体证据。

## 指令（模板）

```
下面是一组同属 (话题, 机制) 的证据单元。请：
1. 概括它们共同反映的问题（不夸大、不下因果结论）；
2. 列出支撑的 source_evidence_ids；
3. 标注平台覆盖与是否单平台；
4. 明确这是草稿、未经人工复核。
输出 JSON：{ "statement": "...", "source_evidence_ids": [...],
            "platform_coverage": [...], "single_platform": true|false,
            "limitations": "..." }
证据组：{{evidence_group}}
```

## 约束

至少 5 条证据才算高支持；不得把相关性表述成因果；不得把置信度写成证据强度。
