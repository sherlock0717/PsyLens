# Phase 1A 线上复核说明

> 本文件记录对提交 `f5a3cf24bd57f7828f68abd1242d3ac7b82b9ca3` 与 `f53a48a755c3f38baa7b43bd6c4ab988d2c8b0ec` 的线上复核。它不修改历史公开数据、页面或 `main`。

## 复核结论

Phase 1A 的核心数量和迁移方向成立：360 条样本建立了平台前缀 ID，695 条唯一命中证据完成迁移，2 条歧义证据被隔离，B 站 120 条样本形成 279 条候选单元，分层状态保持 `legacy_status=BLOCKED`、`v2_migration_status=PASS`、`publication_readiness=BLOCKED`。

在进入 Phase 1B 人工复核与标注前，必须完成以下工程修正。

## 必须修正

### 1. 测试不得改写已提交的 `data/v2/`

当前 `test_v2_build_is_deterministic` 直接调用两次 `build_v2.main()`。生成器会在固定目录 `data/v2/` 重写全部文件，并用当前时间和当前 HEAD 重写 `v2_manifest.json`。

这意味着：

- pytest 会修改 tracked 文件；
- 测试后工作树可能变脏；
- 已提交 manifest 的 `generated_at` 和 `source_commit` 会被测试运行环境覆盖；
- 当前测试只比较 5 个 CSV 的哈希，没有验证整个生成包字节级确定性。

修正要求：

- 生成器支持显式 `output_dir`；
- 测试使用 `tmp_path`，不得写入仓库中的 `data/v2/`；
- `generated_at` 与 `source_commit` 支持显式传入；
- 固定参数下，CSV 与 manifest 均应产生一致结果；
- 增加测试：pytest 前后 tracked `data/v2/` 内容不变。

### 2. 明确“确定性”的边界

当前脚本文档声称“相同输入产生相同结果”，但 manifest 使用当前时间和当前 HEAD，因此整个输出包并非字节级确定。

应选择并落实一种口径：

- 推荐：核心生成函数接收固定 `generated_at`、`source_commit`，使正式快照可完整复现；
- 临时交互运行可以使用当前时间，但必须明确它会改变运行元数据；
- 报告不得把动态 manifest 与确定性 CSV 混称为全部确定性。

### 3. sample ID 不能依赖输入行顺序

当前 `build_sample_ids` 按 clean CSV 的遍历顺序递增编号。若同一批数据仅发生行重排，sample ID 会变化，与文档中的“一经生成，不因排序或重新合并而改变”不一致。

修正要求：

- 对当前冻结迁移，按 `platform_source + numeric legacy_clean_id` 的稳定顺序分配；或读取已冻结的权威迁移表；
- 增加测试：打乱输入行顺序后，`legacy_clean_id -> sample_id` 映射保持不变；
- 文档说明稳定性只针对冻结的 legacy 样本集合，不宣称跨数据重建自动稳定。

### 4. evidence unit index 不应因缺失单元被压缩

当前 `build_evidence_v2` 使用每个 sample 的连续计数器重新编号。若某条歧义证据位于中间，后续已迁移证据的 ID 会前移；歧义证据补回时可能导致 ID 漂移。

当前两条歧义恰好位于各自 legacy 单元序列末尾，因此现有输出未发生实际冲突，但生成规则仍需加固。

修正要求：

- 对 legacy 迁移证据优先保留 `_uN` 中的 N 作为 `unit_index`；
- 检测同一 sample 下的 unit index 冲突；
- 不允许未来解决歧义时改写既有 evidence ID；
- 增加测试：迁移证据的 `unit_index` 与 legacy evidence 后缀一致。

### 5. v2 审计需补齐完整性检查

当前审计已覆盖主要数量与引用，但还需增加：

- manifest `platform_counts`、`bili_samples_pending`、`bili_candidate_unit_count` 与实际一致；
- manifest `source_files` 使用仓库内 POSIX 路径；
- `samples_v2.raw_text/source_url` 与 legacy clean 对应字段逐行一致；
- `id_migration` 完整覆盖 360 samples、695 migrated evidence、2 ambiguous evidence 和 deferred insight/action；
- B 站队列 sample 集合与 Bili samples **完全相等**，不只是子集；
- queue_id 唯一；
- 每个 sample 内 candidate_unit_index 唯一且连续；
- candidate_unit_text 可在对应 sample.raw_text 中定位；
- 队列 raw_text 与 samples_v2 一致；
- `candidate_status=pending_review`、`human_review_status=not_reviewed` 全量检查。

### 6. `source_commit` 应表达来源快照，而非测试时 HEAD

当前生成器读取当前 HEAD。正式 v2 快照的来源是 Phase 0 验收提交 `371d245...`，而不是每次测试时所在的提交。

修正要求：

- 将字段改为更明确的 `source_data_commit`；
- 通过参数显式传入；
- 可另设 `generator_commit`，但不得用测试时 HEAD 覆盖来源快照；
- 路径使用 `.as_posix()`，避免 Windows 反斜杠进入跨平台 manifest。

## 当前状态

- Phase 1A 数据迁移方向：通过；
- Phase 1A 工程验收：待上述修正后通过；
- 不合并 `main`；
- 不修改 Pages；
- 不开始 B 站正式机制标注；
- 不生成结构化洞察或正式行动建议；
- 下一步先完成 `PSYLENS-PHASE1A-002` 生成器与审计加固。