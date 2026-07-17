# 数据关联审计（DATA_LINKAGE_AUDIT）

> 任务：PSYLENS-AUDIT-001 → 002（方法与口径修正）。所有数字由 `tools/audit_public_data.py` 离线、确定性重算，未修改任何历史公开数据。
> 结论先行：**审计状态 = BLOCKED**。核心阻断为「证据表 `parent_id` 与公开整洁样本 `id` 空间系统性错位」。
>
> **口径说明**：本报告只声明「**证据文本可在公开整洁样本中定位**」，**不据此声称采集真实性 / 来源真实性 / 标签真实性 / 人工复核真实性**。

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

### 3.1 拆分两个指标（废止笼统的「parent_id 通过率」）

| 指标 | 定义 | 本轮值 |
| --- | --- | --- |
| **parent_reference_exists_rate** | `parent_id` 值能找到同编号 clean 行的比例 | **1.0**（697/697） |
| **parent_semantic_linkage_rate** | `unit_text` 能匹配声明 parent `raw_text` 的比例 | **0.0**（0/697） |

两指标必须**同时展示**：引用编号都存在，但没有任何一条证据文本真的来自它所声明的父样本。

对声明 parent 的匹配状态（精确子串 / 归一化子串 / SequenceMatcher / 字符 3-gram overlap）：`no_match = 697`，其余状态 0。

### 3.2 全域匹配（多候选感知）

对每条 `unit_text` 在**任意**整洁样本中做归一化子串搜索，**收集所有候选**（`candidate_clean_ids` / `candidate_count`），并按候选数分类：

| 全域匹配分类 | 数量 |
| --- | --- |
| found_in_declared_parent | 0 |
| **unique_match_in_other_id**（candidate_count==1，命中于其他 id） | **695** |
| **ambiguous_match_in_other_ids**（candidate_count>1，来源不确定） | **2** |
| not_found_anywhere | **0** |

口径修正：**只有 `candidate_count == 1` 时**才认定 `actual_clean_id / actual_platform / actual_window / offset`；歧义命中**不指定平台、不计入平台分布、不计算确定 offset**。

- **唯一命中偏移直方图：`{+120: 695}`**（纯 +120，无杂项）。
- 上一轮出现的 `+56 / -56 / Bili 1` 三项，经多候选核查确认为**歧义命中**（下 §3.3），已从确定 offset 与平台分布中剔除。

歧义命中 2 例：

| evidence_id | 声明 parent | candidate_count | 候选 clean id | 候选平台 |
| --- | --- | --- | --- | --- |
| `83_u2` | 83 | 2 | 139, 203 | NGA |
| `96_u3` | 96 | 6 | 40,42,63,170,216,334 | Bili/NGA/Tieba（极短文本，跨平台散布） |

结构结论：公开整洁样本排序为 `[Bili 1–120][NGA 121–240][Tieba 241–360]`；证据 `parent_id` 仅覆盖 `1–240`，695 条精确 `+120` → 实际对应 clean `121–360`（NGA+Tieba）。证据表由一份**仅含 NGA+Tieba（240 条）**的输入从 1 编号生成，公开整洁样本在前面追加 Bili（120）并整体重编号，导致 `parent_id` 整体偏移 +120。

### 3.3 证据单元「实际出处」平台分布（仅唯一命中）

| 平台 | 唯一命中证据单元数 |
| --- | --- |
| NGA | 394 |
| Tieba | 301 |
| （歧义命中 2 条不计入任何平台） | 2 |

**证据层实际只覆盖 NGA 与 Tieba；B 站样本（clean 1–120）在证据层无确定覆盖**（上一轮「Bili 1」为歧义命中误计，已剔除）。这与样本层「三平台各 120」形成层级不一致，不得据此把 B 站计入证据层平台覆盖。

## 4. evidence_phrase 与标签

- `evidence_phrase` 非空 696 条；其中 **695 条**为 `unit_text` 的精确子串（1 条不匹配，需人工核对）。
- `mechanism_label` 全部合法（competence_frustration 268 / uncertain 336 / fairness_threat 72 / trust_communication_gap 10 / belonging_drop 8 / norm_safety_risk 3）；非法值 0。
- `surface_topic` 全部合法；`confidence` 全部合法（medium 268 / low 336 / high 93）。
- 证据表 `raw_text` 列**全为空**（与 `DATA_DICTIONARY.md` 一致）；回溯原文只能靠 `parent_id`，而该链路已错位。

## 5. 洞察关联

- 19 条洞察全部可解析；`supporting_ids` 均非空。
- **所有 supporting_ids 都存在于证据表 `id` 中（缺失 0）**，`supporting_id` 通过率 = 100%。
- 洞察间证据**无重复使用**（reused_evidence_id_count = 0）。
- confidence 与 needs_human_review 是**不同字段**，分别统计：`confidence=high` **7 条**；`needs_human_review=false`（模型输出字段）**8 条**；两者交集 **7 条**。`needs_human_review` **不等于人工复核状态**。
- topic / mechanism 与洞察文本一致性：逐条一致。
- 平台覆盖（按**唯一命中的实际出处**重算，歧义命中不计平台）：19 条中多条为单平台支撑（含高置信主线 line 1 balance×competence，仅 NGA、仅 w1）。详见 `PUBLIC_CLAIM_AUDIT.md`。

## 6. 逐单元明细

- 证据单元逐行关联表：由 `python tools/audit_public_data.py --csv-out <path>` 生成（列：evidence_id, parent_id, linkage_status, substring_match, similarity_ratio, ngram_overlap, evidence_text, parent_text_excerpt, notes）。
- ID 不匹配清单（含每条实际出处 clean id）：见 `docs/audit/ID_MISMATCH_REPORT.csv`。

## 7. 修复方向（本阶段不执行）

1. 重新对齐 `parent_id`：对**唯一命中**的 695 条以真实 clean id 修复；对 2 条**歧义命中**需人工确认后再定，不得机械 +120。
2. 明确证据层实际只覆盖 NGA+Tieba，并据此调整所有「三平台」层级的表述与统计。
3. 决定是否为 Bili 样本补做证据抽取，使证据层与样本层平台一致。
4. 建立稳定、带平台前缀的 ID 体系（见 `PHASE0_SUMMARY.md` 建议 schema）后再迁移。
5. 修复后，`tools/audit_public_data.py` 应重跑至 `parent_semantic_linkage_rate = 1.0`。
