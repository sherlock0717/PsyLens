# 表层话题编码手册（SURFACE_TOPIC_CODEBOOK）

> 表层话题标注一条反馈**在谈什么**（可观察的主题），与机制标签（**为什么**产生负面体验）正交。
> 取值固定为下表九项，不得新增。允许「一条证据一个主话题」。

## 使用总则

- 优先分配**一个主话题**；若明显跨两个话题，取证据文本重点所在。
- 无法判定或信息不足时使用 `other_uncertain`。
- 表层话题独立于机制：同一话题可对应不同机制（如 `balance` 既可能触发 `competence_frustration` 也可能触发 `fairness_threat`）。

## 标签总览

| 标签 | 中文名称 | 纳入要点 | 正例 |
| --- | --- | --- | --- |
| rewards | 奖励与产出 | 掉落、奖励、产出、性价比、任务回报 | 「做任务的奖励太寒酸」 |
| matchmaking | 匹配与对局分配 | 匹配机制、队友质量、段位分配、排队 | 「匹配的队友像人机」 |
| progression | 成长与养成 | 升级、养成线、肝度、进度、门槛 | 「养成线太长太肝」 |
| balance | 平衡与数值 | 英雄/装备/机制强度、数值、改动强弱 | 「这英雄超模了」 |
| new_player_onboarding | 新手引导与体验 | 新手教程、入门门槛、萌新友好度 | 「新手根本看不懂」 |
| community_conflict | 社区冲突与氛围 | 玩家间争执、举报纠纷、圈子氛围、对立 | 「红叉区互喷成一团」 |
| communication_transparency | 沟通与透明度 | 公告、更新说明、官方回应、暗改 | 「暗改也不发公告」 |
| event_design | 活动与玩法设计 | 限时活动、玩法模式、活动规则设计 | 「这活动规则设计得反人类」 |
| other_uncertain | 其他/不确定 | 无法归入上列或信息不足 | 「没了」 |

## 逐标签说明（纳入 / 排除 / 边界）

### rewards（奖励与产出）
- 纳入：奖励数量/质量、产出效率、任务回报、性价比。
- 排除：抱怨养成太长但不提奖励本身 → `progression`。
- 边界：与 progression 的区别在于焦点是「奖励本身」还是「成长路径长度」。

### matchmaking（匹配与对局分配）
- 纳入：匹配算法、队友/对手质量、段位、排队时长。
- 排除：单纯抱怨某英雄强 → `balance`。
- 边界：与 community_conflict 区别在于焦点是「系统匹配」还是「玩家互动冲突」。

### progression（成长与养成）
- 纳入：等级、养成线、肝度、进度门槛。
- 排除：奖励本身寒酸 → `rewards`。

### balance（平衡与数值）
- 纳入：英雄/装备/机制强弱、数值、改动方向。
- 排除：改动没公告 → `communication_transparency`。

### new_player_onboarding（新手引导与体验）
- 纳入：教程、入门门槛、萌新友好度。
- 排除：老玩家养成太肝 → `progression`。

### community_conflict（社区冲突与氛围）
- 纳入：玩家间争执、对立、举报纠纷、圈子氛围恶化。
- 排除：外挂/辱骂等安全议题在机制层归 `norm_safety_risk`；但表层话题仍可为 community_conflict。

### communication_transparency（沟通与透明度）
- 纳入：公告、更新说明、官方回应、暗改、承诺兑现。
- 排除：纯数值强弱 → `balance`。

### event_design（活动与玩法设计）
- 纳入：限时活动、玩法模式、活动规则设计合理性。
- 排除：活动奖励寒酸（焦点在奖励）→ `rewards`。

### other_uncertain（其他/不确定）
- 纳入：无法归入上列、跨多话题且无重点、信息不足。
- 要求：与机制的 `uncertain` 一样，是合法且必要的取值。

## 与机制标签的关系

表层话题与机制标签**多对多**。示例：

| 表层话题 | 常见机制 |
| --- | --- |
| balance | competence_frustration / fairness_threat |
| matchmaking | fairness_threat / norm_safety_risk（代练外挂）|
| rewards | competence_frustration（投入无回报）|
| communication_transparency | trust_communication_gap |
| community_conflict | belonging_drop / norm_safety_risk |

> 编码时先判表层话题（在说什么），再判机制（为什么难受），两者分别记录、互不覆盖。
