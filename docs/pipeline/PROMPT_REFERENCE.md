# Prompt 参考（PROMPT_REFERENCE）

> Demo 默认 mock 不使用提示词；以下为真实 provider 运行时的参考，与 codebook 一致。

| 阶段 | 提示词文件 | 目标 |
| --- | --- | --- |
| 证据抽取 | `demo/prompts/evidence_extraction.md` | 从原文切出可判断的证据单元 |
| 主题编码 | `demo/prompts/topic_coding.md` | 分配表层话题（限 codebook 九项） |
| 机制编码 | `demo/prompts/mechanism_coding.md` | 分配心理机制（限 codebook 六项） |
| 洞察生成 | `demo/prompts/insight_generation.md` | 聚合为结构化洞察 |
| 建议生成 | `demo/prompts/action_generation.md` | 转化为待验证产品假设 |

约束：
- 标签取值严格限定 codebook；
- 证据不足用 uncertain / other_uncertain，不强行归类；
- 不把相关性写成因果，不把置信度写成证据强度；
- 统一术语「结构化洞察 / 待验证产品假设」，禁用「已验证 / 可直接采信 / 应立即实施」。

legacy 阶段实际使用的 prompts 未纳入公开仓库（见 `FULL_PIPELINE.md` 缺失项）。
