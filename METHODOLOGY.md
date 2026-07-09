# PsyLens Methodology（方法论）

> 本文件解释 PsyLens 的数据输入、处理链路、标签体系、证据链与 AI 辅助边界。
> 描述以仓库现有公开文件与 `scripts_public/` 脚本的实际行为为准，不虚构未实现的步骤。

---

## 1. 数据输入

- **来源**：NGA、贴吧、B 站三平台的**公开**社区反馈（帖子正文、楼层回复、视频热评与最新评论等）。
- **整洁样本文件**：`docs/files/input_feedback_phase2_multiplatform_clean.csv`，360 条，三平台各 120 条。
- **字段结构**（详见 `DATA_DICTIONARY.md`）：
  `id, source_type, date, channel, raw_text, url, segment_guess, platform_source, window_tag, theme_bucket, thread_or_video_title, reply_type`。

---

## 2. 处理链路

```
Public Feedback
  → Precleaning
  → AI-assisted Curation
  → Balanced Merge
  → Evidence Unit Extraction
  → Surface Topic Coding
  → Mechanism Coding
  → Insight Validation
  → Action Matrix
```

### 2.1 Precleaning（预清洗）
- 目的：去掉空白、过短、图片路径、论坛 reply 头等明显噪声。
- 输入：各平台 registry 文本。
- 输出：preclean 文件。
- 对应脚本：`scripts_public/preclean_feedback_registry.py`。
- 人工判断边界：清洗规则为启发式，边界样本仍可能保留噪声。

### 2.2 AI-assisted Curation（AI 辅助精修）
- 目的：补齐 `cleaned_text`、`keep_ai`、`theme_bucket`、`mechanism_prior`、`info_score` 等字段，并给出剔除理由。
- 输入：preclean 文件。
- 输出：AI 精修文件。
- 对应脚本：`scripts_public/ai_curate_feedback.py`（通过环境变量调用模型）。
- 人工判断边界：`keep_ai`、`theme_bucket`、`mechanism_prior` 均为 **AI 先验**，需后续复核。

### 2.3 Balanced Merge（按平台平衡合并）
- 目的：把多平台 AI 精修结果合并成统一字段结构，并按平台平衡样本（默认每平台 120 条）。
- 输入：多个平台的 AI 精修 CSV。
- 输出：`docs/files/input_feedback_phase2_multiplatform_clean.csv`。
- 对应脚本：`scripts_public/merge_phase2_inputs.py`。
- 人工判断边界：平衡样本是**为了跨平台可比**，不等于自然舆情分布。

### 2.4 Evidence Unit Extraction（证据单元拆分）
- 目的：把一条整洁样本拆成多个可独立判断的证据单元（一条反馈常含多个诉求）。
- 输入：整洁样本。
- 输出：`docs/files/final_evidence_table.csv` 中的 `unit_text` 行（id 形如 `1_u1`、`1_u2`，`parent_id` 指回原样本）。
- 对应脚本：`scripts_public/run_pipeline.py`（依赖 prompts/config，公开仓库未含，见 `REPRODUCIBILITY.md`）。

### 2.5 Surface Topic Coding（表层主题编码）
- 目的：为每个证据单元标注 `surface_topic`（如 balance、matchmaking、community_conflict、rewards、progression、new_player_onboarding、other_uncertain）。
- 输出：`final_evidence_table.csv` 的 `surface_topic` 字段（并有 `reason_short` 记录判断理由）。

### 2.6 Mechanism Coding（机制编码）
- 目的：为每个证据单元标注心理机制标签 `mechanism_label` 与置信度 `confidence`。
- 输出：`final_evidence_table.csv` 的 `mechanism_label`、`confidence` 字段。

### 2.7 Insight Validation（洞察验证）
- 目的：把带标签证据按共现频率/强度收束成洞察，并标注是否需人工复核。
- 输出：`docs/files/04_validated_insights.jsonl`（19 条），字段含 `insight`、`supporting_ids`、`frequency_type`、`confidence`、`needs_human_review`。
- 人工判断边界：`needs_human_review: true` 的洞察证据有限，需人工复核后再使用。

### 2.8 Action Matrix（行动建议矩阵）
- 目的：把验证洞察压缩为分层行动建议（safe / balanced / bold）。
- 输出：`docs/files/05_action_matrix.json`，字段含 `insight_statements`、`mechanism_hypotheses`、`action_proposals{safe, balanced, bold}`。
- 人工判断边界：该矩阵为 **AI 生成/辅助生成的产品假设**，需配合人工判断。

---

## 3. 标签体系

- **surface_topic**（证据单元的表层主题）：观察到的取值包括 balance、matchmaking、community_conflict、rewards、progression、new_player_onboarding、other_uncertain 等。
- **theme_bucket**（整洁样本层的主题桶，由 AI 精修给出）：观察到的取值包括 balance_mechanic、hero_experience、team_interaction、fairness_attribution、off_topic。
  > 注：`surface_topic`（证据层）与 `theme_bucket`（样本层）属于不同层级的主题字段，使用时请区分。
- **mechanism_label**（心理机制标签）：观察到的取值包括 competence_frustration（胜任受挫）、fairness_threat（公平威胁）、trust_communication_gap（信任/沟通缺口）、belonging_drop（归属感下降）、norm_safety_risk（规范/安全风险）、uncertain（不确定）。
- **confidence**（置信度）：high / medium / low。
- **needs_human_review**（是否需人工复核）：布尔值；true 表示证据有限、需人工确认。

---

## 4. 证据链（如何回溯）

证据链的核心在于 `docs/files/final_evidence_table.csv` 与 `docs/files/04_validated_insights.jsonl` 之间的 id 关联：

1. 每条 validated insight 带有 `supporting_ids`（如 `["1_u2", "2_u2", ...]`）。
2. 每个 id 对应 `final_evidence_table.csv` 中的一行证据单元：
   - `id`：证据单元编号（形如 `1_u2`）。
   - `parent_id`：所属原始样本编号（如 `1`）。
   - `unit_text`：该证据单元的文本。
   - `surface_topic` / `mechanism_label` / `confidence`：主题、机制与置信度。
   - `evidence_phrase`：支撑判断的关键短语。
3. 通过 `parent_id` 可回到整洁样本 `input_feedback_phase2_multiplatform_clean.csv`，进一步查看 `raw_text` 与 `url` 等来源信息。

> 说明：`final_evidence_table.csv` 中观察到部分行的 `raw_text` 列为空；回溯原始文本时应结合 `parent_id` 关联到整洁样本，并以实际文件为准。

---

## 5. AI 辅助边界

- AI 参与了**清洗、分类与生成**（精修、主题/机制先验、洞察收束、行动建议）。
- AI 结果**需要人工复核**，尤其是 `mechanism_prior`、`theme_bucket` 与带 `needs_human_review: true` 的洞察。
- **不把 AI 输出视为自动真值**；对外结论应与证据表、验证洞察及人工复核边界一起阅读。
- `05_action_matrix.json` 属 AI 生成/辅助生成，仅作为产品假设。

---

## 6. 方法局限

- **社区公开样本偏差**：只覆盖公开发声者，不代表沉默多数或全体玩家。
- **平台表达风格差异**：NGA、贴吧、B 站的语气与议题侧重不同，可能影响可比性。
- **标签解释性**：机制标签是解释性框架，不是临床或心理测量。
- **行动建议定位**：仅为基于公开反馈的产品假设，不代表任何企业内部判断。
