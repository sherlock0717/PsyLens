# Prompt 参考：主题编码（topic_coding）

> 仅供真实 provider 参考；Demo 默认 mock 不使用。

任务：为一个证据单元分配一个表层话题，取值严格限定于 `docs/methodology/SURFACE_TOPIC_CODEBOOK.md`：
rewards / matchmaking / progression / balance / new_player_onboarding /
community_conflict / communication_transparency / event_design / other_uncertain。

要求：
- 只判"在说什么"，不判"为什么难受"（后者是机制）；
- 信息不足用 other_uncertain，不强行归类。

输出：`{"surface_topic": "..."}`
