# Prompt 模板：主题编码（topic_coding）

> 状态：`reconstructed_template`。公开模板，不保证与历史运行逐字一致。
> 标签取值见 `docs/methodology/SURFACE_TOPIC_CODEBOOK.md`。

## 指令（模板）

```
给下面的证据单元指定一个表层话题，取值只能来自：
rewards / matchmaking / progression / balance / new_player_onboarding /
community_conflict / communication_transparency / event_design / other_uncertain
判不准时用 other_uncertain，不要强行归类。
输出 JSON：{ "surface_topic": "...", "reason": "..." }
证据：{{unit_text}}
```
