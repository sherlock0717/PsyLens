# 数据关联审计（DATA_LINKAGE_AUDIT）

> 任务：PSYLENS-AUDIT-001 / Phase 0。所有数字由 `tools/audit_public_data.py` 离线、确定性重算，未修改任何历史公开数据。
> 结论先行：**Phase 0 = BLOCKED**。核心阻断为「证据表 `parent_id` 与公开整洁样本 `id` 空间系统性错位」。

## 1. 数据规模与唯一性

| 文件 | 记录数 | 期望 | id 唯一 | 备注 |
| --- | --- | --- | --- | --- |
| `input_feedback_phase2_multiplatform_clean.csv` | 360 | 360 | 是（0 空、0 重复、全整数） | 平台 Bili/NGA/Tieba 各 120 |
| `final_evidence_table.csv` | 697 | 697 | 是（无重复 id） | `parent_id` 范围 1–240（distinct 240） |
| `04_validated_insights.jsonl` | 19 | 19 | — | 逐行可解析，解析失败 0 |
| `05_action_matrix.json` | 1 对象 | — | — | 可解析 |

整洁样本字段与证据表字段均与 `DATA_DICTIONARY.md` 描述一致。

## 2. 整洁样本关键分布

- 平台：`Bili 120 / NGA 120 / Tieba 120`。
- 时间窗：`w1 260 / w2 100`。
- theme_bucket（样本层）：`balance_mechanic 236 / team_interaction 60 / hero_experience 58 / fairness_attribution 6`（off_topic 0）。
- reply_type：`recent_reply 318 / op_context 42`。
- `raw_text` 空 0；`url` 空 0；**`date` 空 240**（仅 NGA 120 条带日期，Bili/Tieba 无日期）。
- URL 域名：`www.bilibili.com 120 / bbs.nga.cn 120 / tieba.baidu.com 120`。
- 精确重复文本组 0；高相似（≥0.90）文本对 0。

## 3. 证据单元与 parent 关联（核心问题）

对 697 条证据单元的 `unit_text` 与其**声明 `parent_id`** 对应的整洁样本 `raw_text` 做匹配（精确子串 / 归一化子串 / SequenceMatcher / 字符 3-gram overlap）：

| 关联状态（vs 声明 parent） | 数量 |
| --- | --- |
| exact_substring / normalized_substring / high_similarity / partial_overlap | 0 |
| **no_match** | **697** |
| missing_parent（parent_id 值不存在） | 0 |
| empty_text | 0 |

**`parent_id` 通过率（值存在）= 100%（0 缺失），但按声明 parent 回溯原文的文本匹配率 = 0%。**

### 3.1 全域诊断：数据真实，只是 id 错位

对每条 `unit_text` 在**任意**整洁样本中做归一化子串搜索：

| 全域匹配 | 数量 |
| --- | --- |
| found_in_declared_parent | 0 |
| **found_in_other_id** | **697** |
| not_found_anywhere | **0** |

即：**全部 697 条证据文本都真实存在于整洁样本中**（数据不是伪造），但**都出现在与其 `parent_id` 不同的 `id` 上**。

`parent_id` 偏移直方图：`{+120: 695, +56: 1, -56: 1}`。

- 公开整洁样本排序为 `[Bili 1–120][NGA 121–240][Tieba 241–360]`。
- 证据表 `parent_id` 仅覆盖 `1–240`，且 695/697 精确 `+120` → 实际对应 clean `121–360`（即 **NGA + Tieba**）。
- 结论：证据表由一份**仅含 NGA+Tieba（240 条）**的输入生成并从 1 编号；公开整洁样本在前面追加了 Bili（120 条）并整体重编号，导致 `parent_id` 整体偏移 +120。

### 3.2 证据单元「实际出处」平台分布

| 平台 | 实际来源证据单元数 |
| --- | --- |
| NGA | 395 |
| Tieba | 301 |
| Bili | 1（±56 偏移的短文本偶然命中，非真实覆盖） |

**证据层实际只覆盖 NGA 与 Tieba；B 站样本（clean 1–120）在证据层几乎无覆盖。** 这与样本层「三平台各 120」形成层级不一致。

## 4. evidence_phrase 与标签

- `evidence_phrase` 非空 696 条；其中 **695 条**为 `unit_text` 的精确子串（1 条不匹配，需人工核对）。
- `mechanism_label` 全部合法（competence_frustration 268 / uncertain 336 / fairness_threat 72 / trust_communication_gap 10 / belonging_drop 8 / norm_safety_risk 3）；非法值 0。
- `surface_topic` 全部合法；`confidence` 全部合法（medium 268 / low 336 / high 93）。
- 证据表 `raw_text` 列**全为空**（与 `DATA_DICTIONARY.md` 一致）；回溯原文只能靠 `parent_id`，而该链路已错位。

## 5. 洞察关联

- 19 条洞察全部可解析；`supporting_ids` 均非空。
- **所有 supporting_ids 都存在于证据表 `id` 中（缺失 0）**，`supporting_id` 通过率 = 100%。
- 洞察间证据**无重复使用**（reused_evidence_id_count = 0）。
- `needs_human_review`：true 11 条 / false 8 条。
- topic / mechanism 与洞察文本一致性：逐条一致。
- 平台覆盖（按**实际出处**重算）：19 条中 **12 条为单平台支撑**（含高置信主线 line 1 balance×competence，仅 NGA、仅 w1）。详见 `PUBLIC_CLAIM_AUDIT.md`。

## 6. 逐单元明细

- 证据单元逐行关联表：由 `python tools/audit_public_data.py --csv-out <path>` 生成（列：evidence_id, parent_id, linkage_status, substring_match, similarity_ratio, ngram_overlap, evidence_text, parent_text_excerpt, notes）。
- ID 不匹配清单（含每条实际出处 clean id）：见 `docs/audit/ID_MISMATCH_REPORT.csv`。

## 7. 修复方向（本阶段不执行）

1. 重新对齐 `parent_id`：以 `unit_text` 全域匹配得到的真实 clean id 重写证据表 `parent_id`（或反向：为证据表补一列 `clean_id_resolved`）。
2. 明确证据层实际只覆盖 NGA+Tieba，并据此调整所有「三平台」层级的表述与统计。
3. 决定是否为 Bili 样本补做证据抽取，使证据层与样本层平台一致。
4. 修复后，`tools/audit_public_data.py` 应重跑至 `no_match = 0`。
