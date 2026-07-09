# PsyLens Data Dictionary（数据字典）

> 本字典基于仓库现有公开文件的**实际字段**编写，取值示例来自对公开文件头部的观察。
> 字典**不修改任何数据文件**；如字段取值与本文件描述不一致，请以 `docs/files/` 下实际文件为准。
> 对无法确证含义的字段，本文件如实标注为「需结合实际文件确认」，不做臆测。

---

## 1. `docs/files/input_feedback_phase2_multiplatform_clean.csv`

三平台整洁样本（360 条，三平台各 120）。表头字段如下：

| 字段 | 含义 | 类型 | 是否可为空 | 来源/生成阶段 | 使用注意 |
| --- | --- | --- | --- | --- | --- |
| `id` | 样本编号（整数序号） | 整数 | 否 | 合并阶段 | 与证据表 `parent_id` 关联 |
| `source_type` | 来源类型（观察值如 `Bili`） | 字符串 | 否 | 采集阶段 | 取值以实际文件为准 |
| `date` | 日期 | 字符串/日期 | **是（观察到为空）** | 采集阶段 | 公开文件中观察到部分为空，使用时以实际文件为准 |
| `channel` | 渠道标识（观察值如 `Bili_w1`） | 字符串 | 否 | 采集/合并阶段 | 常见为「平台_时间窗」组合 |
| `raw_text` | 原始反馈文本 | 字符串 | 否 | 采集阶段 | 保留玩家原始表达 |
| `url` | 来源链接 | 字符串 | 可能为空 | 采集阶段 | 用于回溯来源 |
| `segment_guess` | 主题/片段推测（观察值如 `balance_mechanic`） | 字符串 | 可能为空 | AI 精修阶段 | 为推测值，需复核 |
| `platform_source` | 平台来源（NGA / 贴吧 / B 站，观察值如 `Bili`） | 字符串 | 否 | 采集阶段 | 用于平台平衡与对比 |
| `window_tag` | 时间窗标签（观察值 `w1` / `w2`） | 字符串 | 否 | 合并阶段 | w1 近期窗口、w2 历史对照窗口 |
| `theme_bucket` | 主题桶（样本层，观察值如 `balance_mechanic`） | 字符串 | 可能为空 | AI 精修阶段 | 取值集见 `METHODOLOGY.md` §3 |
| `thread_or_video_title` | 帖子或视频标题 | 字符串 | 可能为空 | 采集阶段 | 提供上下文 |
| `reply_type` | 文本类型（观察值如 `recent_reply`、`op_context`） | 字符串 | 否 | 采集/合并阶段 | 区分正文与回复类型 |

---

## 2. `docs/files/final_evidence_table.csv`

证据单元表（697 个 evidence unit）。表头字段如下：

| 字段 | 含义 | 类型 | 是否可为空 | 来源/生成阶段 | 使用注意 |
| --- | --- | --- | --- | --- | --- |
| `id` | 证据单元编号（形如 `1_u1`、`1_u2`） | 字符串 | 否 | 证据拆分阶段 | 与洞察文件 `supporting_ids` 关联 |
| `parent_id` | 所属原始样本编号（如 `1`） | 整数/字符串 | 否 | 证据拆分阶段 | 回溯到整洁样本 `id` |
| `unit_text` | 证据单元文本 | 字符串 | 否 | 证据拆分阶段 | 含未清洗的原始表达（可能含粗口） |
| `surface_topic` | 表层主题（如 `balance`、`other_uncertain`） | 字符串 | 否 | 主题编码阶段 | 取值集见 `METHODOLOGY.md` §3 |
| `reason_short` | 判断理由（英文简述） | 字符串 | 可能为空 | 编码阶段（AI 辅助） | 为解释性说明，非事实断言 |
| `mechanism_label` | 心理机制标签（如 `competence_frustration`、`fairness_threat`、`uncertain`） | 字符串 | 否 | 机制编码阶段 | 取值集见 `METHODOLOGY.md` §3 |
| `confidence` | 置信度 | 字符串 | 否 | 编码阶段 | 取值 high / medium / low |
| `evidence_phrase` | 支撑判断的关键短语 | 字符串 | 可能为空 | 编码阶段 | 用于快速定位证据 |
| `raw_text` | 原始文本 | 字符串 | **是（观察到为空）** | 证据拆分阶段 | 公开文件中观察到该列为空，回溯原文请经 `parent_id` 关联整洁样本，并以实际文件为准 |

---

## 3. `docs/files/04_validated_insights.jsonl`

验证洞察文件（每行一个 JSON 对象，共 19 条）。字段如下：

| 字段 | 含义 | 类型 | 是否可为空 | 来源/生成阶段 | 使用注意 |
| --- | --- | --- | --- | --- | --- |
| `insight` | 洞察文本（英文，描述某主题与某机制的共现） | 字符串 | 否 | 洞察验证阶段 | 形如「Feedback around [balance] frequently co-occurs with [competence_frustration] signals.」 |
| `supporting_ids` | 支撑该洞察的证据单元 id 列表 | 字符串数组 | 否 | 洞察验证阶段 | 与证据表 `id` 关联，用于回溯 |
| `frequency_type` | 频率类型 | 字符串 | 否 | 洞察验证阶段 | 观察值：`high_frequency`、`high_intensity_or_low_frequency` |
| `confidence` | 置信度 | 字符串 | 否 | 洞察验证阶段 | 观察值：high / medium / low |
| `needs_human_review` | 是否需人工复核 | 布尔 | 否 | 洞察验证阶段 | true 表示证据有限、需人工确认 |
| `error` | 错误信息字段 | — | — | — | **当前公开文件中未观察到该字段**；如后续版本出现，应记录处理异常的说明 |

---

## 4. `docs/files/05_action_matrix.json`

行动建议矩阵（单个 JSON 对象，AI 生成/辅助生成）。结构如下：

| 字段 | 含义 | 类型 | 是否可为空 | 来源/生成阶段 | 使用注意 |
| --- | --- | --- | --- | --- | --- |
| `insight_statements` | 洞察陈述列表（英文） | 字符串数组 | 否 | 行动矩阵生成阶段 | 对关键洞察的自然语言概述 |
| `mechanism_hypotheses` | 机制假设列表（英文） | 字符串数组 | 否 | 行动矩阵生成阶段 | 为**假设**，非结论 |
| `action_proposals` | 行动建议集合 | 对象 | 否 | 行动矩阵生成阶段 | 含 safe / balanced / bold 三个子字段 |
| `action_proposals.safe` | 稳妥类建议 | 字符串数组 | 否 | 行动矩阵生成阶段 | 低风险、可先行 |
| `action_proposals.balanced` | 平衡类建议 | 字符串数组 | 否 | 行动矩阵生成阶段 | 中等投入 |
| `action_proposals.bold` | 进阶类建议 | 字符串数组 | 否 | 行动矩阵生成阶段 | 高投入/高影响 |

> 整份文件为 **AI 生成/辅助生成的产品假设**，使用时需配合人工判断，不代表任何企业内部决策。

---

## 通用使用说明

1. 所有字段含义以仓库实际文件为最终依据；本字典描述基于对公开文件的观察。
2. 观察到为空的字段（如整洁样本的 `date`、证据表的 `raw_text`）在使用时以实际文件为准，不应假设其一定有值。
3. 本字典不修改任何数据文件，也不新增或改动数据内容。
