# Prompt 模板：结构化观察生成

> 状态：公开重构模板，用于定义外部 provider 的输入输出契约。

## 目标

将同一“表层话题 × 体验机制”的证据组合为可核查的结构化观察，并保留数量、平台与来源证据。

## 指令模板

```text
下面是一组属于同一表层话题与体验机制的证据单元。请：

1. 概括证据共同呈现的问题，不扩展到证据之外；
2. 列出 source_evidence_ids；
3. 记录 evidence_count、platform_coverage 与 single_platform；
4. 说明统计分母和纳入规则；
5. 把抽样、编码来源、上下文和因果解释限制集中写入 limitations。

输出 JSON：
{
  "statement": "...",
  "source_evidence_ids": ["..."],
  "evidence_count": 0,
  "platform_coverage": ["..."],
  "single_platform": true,
  "denominator": "...",
  "limitations": "..."
}

证据组：{{evidence_group}}
```

## 约束

- 不把共现关系写成因果；
- 不把模型置信度写成证据强度；
- 单平台结果不扩展为跨平台结论；
- `uncertain` 证据不强行归入具体机制；
- 支持等级应同时考虑证据数量、平台覆盖和证据独立性，不能只设置固定数量门槛。
