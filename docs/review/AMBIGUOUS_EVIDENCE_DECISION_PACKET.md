# 歧义证据决策审查包（AMBIGUOUS_EVIDENCE_DECISION_PACKET）

> 两条 legacy 证据的 `unit_text` 在整洁样本中**多候选命中**（来源不确定）。本文件给出完整上下文与推荐处理，但**不自动定案**：`resolution_status` 保持 `pending_human_resolution`，等待用户确认（对应延期决策 D-003）。
> 在用户确认前：不生成正式 `evidence_id`、不进入洞察、不计入公开指标分母、保留在 review queue。

---

## 案例一：`83_u2`

- **legacy evidence id**：`83_u2`
- **unit_text**：「没啥用」
- **候选数**：2
- **候选平台**：NGA（两个候选同平台）

| 候选 clean id | 候选 sample_id | 平台 | 原文节选 |
| --- | --- | --- | --- |
| 139 | NGA_0019 | NGA | 「说实话没啥用，加一起就比循环往复强一点。考虑到还要分三次发给你，循环往复拿到直接就全技能60技能急速」 |
| 203 | NGA_0083 | NGA | 「三个金用起来可能不如两个银凑出来的大法师羁绊 没啥用」 |

- **候选上下文分析**：「没啥用」是极短通用评价，两个 NGA 样本都包含该词，语义上都在讨论「某羁绊/海克斯价值不高」，但**具体指向对象不同**（一个说「循环往复相关」，一个说「三金羁绊」）。
- **推荐处理**：`recommended_resolution = exclude_as_too_short`
- **推荐理由**：「没啥用」本身信息量极低、脱离上下文无独立判断价值；即便归到某一候选，也难以支撑稳定的机制/话题标签。作为独立证据单元价值低。
- **风险**：若强行 `assign_to_candidate`，可能把评价错误绑定到非原始出处；`merge_with_previous_unit` 需要确认同一样本内前一单元存在且语义连续。
- **默认排除影响**：不进入正式证据统计与洞察；对公开指标几乎无影响（单条极短片段）。

---

## 案例二：`96_u3`

- **legacy evidence id**：`96_u3`
- **unit_text**：「没了」
- **候选数**：6
- **候选平台**：Bili / NGA / Tieba（跨三平台）

| 候选 clean id | 候选 sample_id | 平台 | 原文节选 |
| --- | --- | --- | --- |
| 40 | BILI_0040 | Bili | 「…越不平越支持，说娱乐模式就是要不公平…我还是觉得」 |
| 42 | BILI_0042 | Bili | 「过于娱乐化，导致大乱斗本身的竞技性没了…」 |
| 63 | BILI_0063 | Bili | 「…视频只有引战带节奏，娱乐性都没了，看的人头大」 |
| 170 | NGA_0050 | NGA | 「…裂隙触发就三分之一血没了…」 |
| 216 | NGA_0096 | NGA | 「塞拉斯就是对面大招好出ap，不好出ad，没手法别玩，没了」 |
| 334 | TIEBA_0094 | Tieba | 「…好做完任务的时候刚好格子满了，直接给我卡没了」 |

- **候选上下文分析**：「没了」是极短且高频的口语片段，在 6 个不同样本、3 个平台中都出现，语义各异（竞技性没了 / 血没了 / 手法梗「没了」/ 格子卡没了）。**无法确定原始出处**。
- **推荐处理**：`recommended_resolution = exclude_as_too_short`
- **推荐理由**：「没了」是纯口语尾词，跨平台 6 处偶然命中，作为独立证据无稳定语义，且无法确定真实出处。
- **风险**：任何 `assign_to_candidate` 都是猜测，可能造成跨平台错误归属，进而污染平台覆盖统计。
- **默认排除影响**：不进入正式证据统计与洞察；避免虚增平台覆盖。

---

## 汇总建议

| legacy id | unit_text | 候选数 | 推荐 recommended_resolution | recommended_action |
| --- | --- | --- | --- | --- |
| 83_u2 | 没啥用 | 2 | exclude_as_too_short | 从正式证据排除，保留在 review queue |
| 96_u3 | 没了 | 6 | exclude_as_too_short | 从正式证据排除，保留在 review queue |

> 两条均建议**排除**（过短、来源不确定）。但本阶段仅写入 `recommended_resolution / recommended_action`，`resolution_status` 保持 `pending_human_resolution`，最终由用户在 D-003 确认。排除记录写入 `data/v2/evidence_exclusion_log.csv`（阶段 E），标记 `recoverable=yes`。
