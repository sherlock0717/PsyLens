# B 站 Agent 标签提案报告（BILI_AGENT_PROPOSAL_REPORT）

> 对 `data/v2/bili_evidence_queue.csv` 的 279 个候选单元，由本 Agent 依据 codebook 以**确定性本地规则**生成提案（`tools/build_review_infra.py`）。
> **这不是人工复核结果**：全部提案 `proposer_type=agent`、`proposal_status=agent_proposed_unreviewed`、`needs_human_review=true`。
> 未调用任何外部模型 API 或在线模型；相同输入产生相同输出。

## 1. 覆盖与总量

- 候选单元总数：**279**，全部有提案记录（无跳过、未删除原候选）。
- `include_as_evidence` 分布：

| 取值 | 数量 | 占比 |
| --- | --- | --- |
| yes | 69 | 24.7% |
| uncertain | 163 | 58.4% |
| no | 47 | 16.8% |

> `uncertain` 真实使用（58.4%）：大量候选为长评论切出的中间句、上下文依赖片段或机制指向不明确，未为覆盖率强行归类。

## 2. 表层话题分布（surface_topic_proposed）

| 话题 | 数量 |
| --- | --- |
| balance | 78 |
| （空/未判定） | 94 |
| matchmaking | 46 |
| event_design | 24 |
| communication_transparency | 13 |
| progression | 13 |
| rewards | 6 |
| community_conflict | 4 |
| new_player_onboarding | 1 |

> B 站样本高度集中在 `balance`（英雄/装备/数值平衡）与 `matchmaking`（匹配/队友），与该批数据主要为某 MOBA/自走棋平衡讨论一致。空值主要落在 `include=no` 与部分 `uncertain`。

## 3. 机制分布（mechanism_label_proposed）

| 机制 | 数量 |
| --- | --- |
| uncertain | 152 |
| competence_frustration | 40 |
| fairness_threat | 16 |
| trust_communication_gap | 14 |
| norm_safety_risk | 7 |
| belonging_drop | 3 |
| （空，include=no） | 47 |

- `uncertain` 比例（机制层，占全部 279）：**54.5%**；占 `include∈{yes,uncertain}` 的比例更高。
- 机制标签**无超出 codebook**（校验 0 违规）。

## 4. needs_human_review 与置信度

- `needs_human_review = true`：**279（100%）** —— 所有 Agent 提案默认需人工复核。
- `proposal_confidence`：medium 69（对应多数 `yes`）、low 210。
- **不得**把 `proposal_confidence` 解释为证据强度或人工确认。

## 5. evidence_phrase 可定位性

- `evidence_phrase_proposed` 全部可在对应 `candidate_unit_text` 中定位（校验 0 不可定位）。

## 6. 常见冲突类型（提案规则层面）

1. **balance 话题下机制二义**：同一条既像「打不过/数值挫败」（competence）又像「设计不公/恶心玩家」（fairness）。规则按 codebook 冲突优先级取一，人工复核时需重点确认主语气。
2. **community_conflict 与 norm_safety_risk 交叠**：涉及「喷/嘴臭/举报」既是社区氛围也是秩序安全，机制层优先 norm_safety_risk，话题层可能标 community_conflict。
3. **长评论中间句上下文依赖**：如「反甲，属性和价格还算不错」单独看信息不足 → uncertain/no。
4. **建议型/分析型陈述**：如装备改动建议，含机制线索但非情绪抱怨，多判 uncertain。

## 7. 边界声明

- 本报告是 **Agent 提案的统计**，不是人工复核结论；
- 任何标签在人工于 `human_review_log.csv` 记录前，均为 `agent_proposed_unreviewed`；
- 页面与正式结论不得展示这些提案为已确认结果（见 D-004）。
