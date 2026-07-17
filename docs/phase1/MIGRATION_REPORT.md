# 迁移报告（MIGRATION_REPORT）

> PSYLENS-PHASE1A-001 → 002。由 `tools/build_v2_dataset.py` 生成，`tools/audit_public_data.py --dataset v2` 校验。
> 未覆盖任何历史公开数据；unit_text 与 source_url 均未修改。
>
> **确定性口径**：五个 CSV 由固定输入确定性生成；只有在**固定 `generated_at` 与固定 `source_data_commit`** 时，完整 v2 快照（含 `v2_manifest.json`）才字节级可重复生成。临时交互运行使用当前时间，会改变 manifest 运行元数据，届时整包非字节级确定。

## 1. 样本迁移（samples_v2.csv）

- 从公开 clean CSV 的 360 条样本生成，`migration_status = migrated_from_legacy_clean`。
- sample_id 唯一；每平台 120（Bili/NGA/Tieba）；legacy_clean_id 唯一。
- 保留字段：sample_id / legacy_clean_id / platform_source / platform_sequence / window_tag / theme_bucket / reply_type / date / raw_text / source_url / thread_or_video_title / migration_status。
- `raw_text`、`source_url` 原样保留，不新增推测信息。

## 2. 证据迁移（evidence_v2.csv）

- 仅迁移审计器判定为 **唯一命中**（`candidate_count == 1`）的 legacy 证据；
- 迁移数量：**695**（与 Phase 0 唯一命中数一致）；
- `migration_method = unique_normalized_substring_match`；
- 旧标签以 `_legacy` 字段保留（`surface_topic_legacy` / `mechanism_label_legacy` / `confidence_legacy`），并标注 `review_status = legacy_ai_label_unreviewed`；
- **不把 legacy 标签写成已人工确认**；**不把 confidence 解释为证据强度**；unit_text 不修改；
- 每条证据的 unit_text 均可在其对应 sample.raw_text 中定位（审计通过）。

示例（原 `1_u2` → `NGA_0001_U02`）：legacy parent_id=1（错位）→ 经唯一定位解析到真实 clean id=121 → `NGA_0001`。

## 3. 迁移方法与口径

- 「旧证据文本可在公开样本中定位」是本次自动迁移的依据；这**不等于**采集真实性、来源真实性或人工复核。
- 自动迁移只处理唯一命中；歧义证据单独隔离（见 §4）。

## 4. 歧义证据（未自动迁移）

- 数量：**2**（`83_u2`、`96_u3`），写入 `data/v2/ambiguous_evidence_queue.csv`，`resolution_status = pending_human_resolution`。
- 详见 `AMBIGUOUS_EVIDENCE_REVIEW.md`。

## 5. id_migration.csv 覆盖

- 360 条 legacy clean id → sample_id（migrated）；
- 695 条 legacy evidence id → evidence_id（migrated）；
- 2 条歧义证据：new_id 为空，status = pending_human_resolution；
- legacy insight / action **不迁移**，标记 `deferred_until_evidence_rebuild`。

## 6. manifest

- `data/v2/v2_manifest.json` 记录 schema_version、generated_at（显式传入）、`source_data_commit`（显式传入的来源快照 `371d245...`，不再从当前 HEAD 推断）、可选 `generator_commit`、`source_files`（POSIX 相对路径）、各数量、SHA-256 哈希与 limitations。
- 审计已校验 manifest 的数量、`platform_counts`、`bili_samples_pending`、`bili_candidate_unit_count`（与实际队列行数一致，非写死）、`source_data_commit`、`source_files` 路径格式与 SHA-256 一致。

## 7. 当前状态

- v2 迁移底座审计：**PASS**；
- legacy 审计：仍 **BLOCKED**（历史证据链错位未修复）；
- publication_readiness：**BLOCKED**（B 站证据仍在待处理队列，结构化洞察与行动建议尚未重建）。
- v2 **尚不具备公开发布条件**。
