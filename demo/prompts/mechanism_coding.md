# Prompt 参考：机制编码（mechanism_coding）

> 仅供真实 provider 参考；Demo 默认 mock 不使用。

任务：为一个证据单元分配一个心理机制标签，取值严格限定于 `docs/methodology/MECHANISM_CODEBOOK.md`：
competence_frustration / fairness_threat / trust_communication_gap /
belonging_drop / norm_safety_risk / uncertain。

要求：
- 判"为什么产生负面体验"；
- 遵守 codebook 的纳入/排除标准与冲突裁决优先级；
- 证据不足时用 uncertain，不得为覆盖率强行分配；
- 不把相关性表述为因果。

输出：`{"mechanism_label": "...", "evidence_phrase": "..."}`
