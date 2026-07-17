# Phase 0 线上复核说明

> 本文件记录对提交 `20eb1458b7768b91d1d85847adc6ca083c007726` 的二次复核。它用于约束后续修复，不修改历史数据或公开页面。

## 复核结论

Phase 0 的核心发现成立：公开证据表的 `parent_id` 与整洁样本 `id` 空间系统性错位，页面示例 `1_u2` 的来源平台与父样本说明错误。审计分支可作为 Phase 1 的工作基础，但以下口径与方法必须先校正。

## 必须校正的事项

1. **区分引用存在与语义关联。**
   - `parent_id` 值存在率为 100%。
   - 证据文本匹配声明父样本的比例为 0%。
   - 后续不再将前者简称为“parent_id 通过率”，避免误解。

2. **全域匹配需要识别多候选。**
   当前脚本在任意 clean 文本包含 `unit_text` 时采用第一个命中。短文本可能命中多个样本，因此后续需要输出：
   - `candidate_clean_ids`
   - `candidate_count`
   - `unique_global_match`
   - `ambiguous_global_match`

   只有唯一命中才可用于统计实际平台和时间窗。当前 `+120` 的 695 条系统模式可信，但 `+56/-56` 和 “Bili 1 条”不得作为确定来源。

3. **不得把“文本可定位”表述为“数据真实性已证明”。**
   审计只能证明 697 条 `unit_text` 可在公开 clean CSV 中定位，不能据此证明采集真实性、来源真实性或人工复核真实性。

4. **“约 8 条高置信主线”不能直接按 `needs_human_review=false` 验证。**
   `needs_human_review` 是模型输出字段，不等同于 confidence，也不等同于人工确认。后续应分别统计：
   - `confidence=high` 的洞察数；
   - `needs_human_review=false` 的洞察数；
   - 两者交集。

   页面该主张应重新判定，不再标为简单 verified。

5. **不要生成不存在的证据 ID。**
   `source_evidence_ids: ["121_u2"]` 只是示意，但当前数据中不存在该 ID。推荐后续稳定 ID 方案：
   - 样本：`BILI_0001` / `NGA_0001` / `TIEBA_0001`；
   - 证据：`NGA_0001_U02`；
   - 或保留现有 evidence id，并单独修复 `parent_id`。

   在方案确定前，不生成公开建议文件。

6. **DOCX v4 仅作为重写底稿，不直接定为最终正式版。**
   v4 内容更完整，但其中仍继承当前错误证据链、人工复核口径和三平台机制结论。数据修复与页面口径完成后，应基于 v4 生成新的无版本号正式文件，再归档 v3/v4。

7. **当前测试属于问题快照测试。**
   `test_run_audit_is_blocked_due_to_parent_offset` 等测试适合 Phase 0。Phase 1 修复后必须替换为期望状态测试，例如：
   - `parent_semantic_linkage_rate == 1.0`；
   - 页面示例链闭合；
   - supporting IDs 全部可解析；
   - 三平台覆盖主张与实际数据一致。

## Phase 1 推荐路线

不建议只给现有证据表机械加 120。PsyLens 仍定位为多平台、偏评测的可核查分析案例，因此推荐：

1. 建立稳定、带平台前缀的 sample/evidence/insight/action ID；
2. 对 360 条样本统一重建或迁移证据层；
3. 补齐 B 站证据抽取与编码，保证证据层覆盖三平台；
4. 建立真实人工复核日志和 override 记录；
5. 将 `validated insights` 改为“结构化洞察”；
6. 新增可回溯的人工整理产品假设；
7. 建立离线 mock Demo 与数据校验 CI；
8. 数据和主张稳定后再重写 README、页面和正式 DOCX。

## 当前状态

- Phase 0 仍为 `BLOCKED`；
- 不合并至 `main`；
- 不修改 Pages；
- 不直接发布审计报告；
- 下一步在同一审计分支追加方法修正，随后进入独立 Phase 1 修复分支。
