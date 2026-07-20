# Prompt 模板：机制编码（mechanism_coding）

> 状态：`reconstructed_template`。公开模板，不保证与历史运行逐字一致。
> 标签取值与判定见 `docs/methodology/MECHANISM_CODEBOOK.md`。

## 指令（模板）

```
给下面的证据单元指定一个心理机制标签，取值只能来自：
competence_frustration / fairness_threat / trust_communication_gap /
belonging_drop / norm_safety_risk / uncertain
判不准时用 uncertain，不要为覆盖率强行归类；相关不等于因果。
输出 JSON：{ "mechanism_label": "...", "evidence_phrase": "定位短语（原文子串）", "reason": "..." }
证据：{{unit_text}}
```

## 校验

`evidence_phrase` 必须是 `unit_text` 的子串；`mechanism_label` 不得超出六项。
