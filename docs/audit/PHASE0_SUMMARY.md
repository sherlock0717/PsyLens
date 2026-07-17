# PSYLENS-AUDIT-001 · Phase 0 总结

> 只做审计、检测脚本与报告。未修复历史数据、未重写页面、未改 main、未调用真实 API、未运行真实抓取、未读取/创建任何真实 Cookie/Token/Key。
> 全部数字由 `tools/audit_public_data.py` 离线、确定性重算。

## 0. 结论：审计状态 = **BLOCKED**（PSYLENS-AUDIT-002 修正口径后不变）

阻断项（详见各专项报告）：

1. **证据表 `parent_id` 与公开整洁样本 `id` 空间系统性错位**：`parent_reference_exists_rate = 1.0` 但 `parent_semantic_linkage_rate = 0.0`。
2. **页面示例证据 `1_u2` 证据链错误**：页面称 parent_id=1、平台 B 站；实际唯一命中 clean id=121、平台 NGA。

其余为警告级（无人工复核记录、建议无可追溯字段、证据层平台覆盖与样本层不一致、页面下载链接指向较旧 DOCX、隐私两项 requires_decision）。修复方向已在各报告给出。

> **口径纪律**：本审计只声明「证据文本可在公开整洁样本中定位」，**不据此声称采集 / 来源 / 标签 / 人工复核真实性**。`needs_human_review` 是模型输出字段，不等于人工复核状态。

## 1. 关键量化结果（修正后）

| 项 | 值 |
| --- | --- |
| clean 行数 / 唯一 id | 360 / 是（0 空、0 重复） |
| evidence 行数 / 唯一 id | 697 / 是 |
| **parent_reference_exists_rate** | **1.0**（697/697 引用编号存在） |
| **parent_semantic_linkage_rate** | **0.0**（0/697 文本匹配声明 parent） |
| 全域匹配：unique / ambiguous / not_found | **695 / 2 / 0** |
| 唯一命中偏移直方图 | **{+120: 695}**（纯 +120；旧 +56/-56/Bili1 实为歧义命中，已剔除） |
| 实际出处平台（仅唯一命中） | NGA 394 / Tieba 301 / 歧义 2（不计平台） |
| supporting_id 通过率 | 100%（缺失 0、空 0） |
| `1_u2` 示例是否闭合 | **否**（候选数 1，实际 NGA；页面称 B 站错误） |
| uncertain 比例（机制层） | 336/697 ≈ 48% |
| confidence=high / needs_human_review=false / 交集 | **7 / 8 / 7** |
| 行动建议可追溯率 | 0（无 source_insight/evidence 字段） |
| DOCX 结论 | **v4 为重写底稿，非可直接发布正式版** |
| 隐私综合风险 | medium（含 2 项 requires_decision） |

页面主张（共 22 条核对，与 `PUBLIC_CLAIM_AUDIT.md` C01-C22 逐条状态一致）：verified 15、partially_verified 4、unsupported 2、contradicted 1（合计 22）。其中 partially_verified 为 C13/C14/C18/C19，unsupported 为 C16/C17，contradicted 为 C15。详见 `PUBLIC_CLAIM_AUDIT.md`。

## 2. 人工复核实际范围（section 9）

- 仓库中**不存在**：逐行人工复核日志、复核前后标签、复核人/复核类型、全量复核证据。
- 仅有模型字段 `needs_human_review`（`04_validated_insights.jsonl`）及 pipeline 默认返回。
- 页面「经人工复核 / 可以直接采信」**缺乏实际依据**，属需降级表述。
- **不得**据描述文字推断人工复核已完成。

## 3. 行动建议审计与建议 schema（section 10 / 修正）

- `05_action_matrix.json`：纯 AI 生成；含 `insight_statements(3)`、`mechanism_hypotheses(3)`、`action_proposals{safe2,balanced2,bold2}`=6 条。
- **无** `validation_method`、**无** `expected_effect`、**无** `source_insight_ids`/`source_evidence_ids`、**无**人工整理状态。
- 页面 4 张卡为「人工整理」，页面已如实说明与 JSON 非一一对应；但仍无 insight/evidence 级可追溯。

**ID 方案（Phase 1 决策前，不生成实际 `public_action_hypotheses.json`）**：本阶段**仅设计**两种候选方案，且**不写入任何不存在的 evidence_id**（上一轮示意的 `"121_u2"` 已删除；注意 `121_u2` 恰好是真实 id，但用它示意会误导——正式方案的 ID 应经修复后确定）。

- **方案 A（最小改动）**：保留现有 `evidence_id`（如 `1_u2`），**单独修复 `parent_id`** 使其指向真实 clean 行；建议文件的 `source_evidence_ids` 引用修复后的现有 evidence_id。
- **方案 B（稳定平台前缀 ID）**：重建一套带平台前缀、稳定可读的 ID 体系：
  - sample：`BILI_0001` / `NGA_0001` / `TIEBA_0001`
  - evidence：`NGA_0001_U02`
  - insight：`INSIGHT_001`
  - action：`ACTION_001`

建议 schema（字段设计，占位符不代表真实数据）：

```json
{
  "action_id": "ACTION_001",
  "title": "...",
  "summary": "...",
  "source_insight_ids": ["INSIGHT_001"],
  "source_evidence_ids": ["<修复/重建后的真实 evidence_id>"],
  "evidence_summary": "...",
  "expected_effect": "...",
  "validation_method": "...",
  "review_status": "human_curated",
  "limitations": "..."
}
```

> 在 Phase 1 选定方案并完成 ID 修复/重建前，**不得**据现有错位数据生成 `public_action_hypotheses.json`。

## 4. 旧页面与文档审计（section 15，仅列位置与建议，不改文件）

- `docs/index.md`：文件开头已自述「早期 Markdown 摘要，仅作历史记录」。建议**移入 archive**或删除，不再作为第二套页面正文维护。其结论数字（360/w1 260/w2 100）与 index.html 一致。
- 重复边界说明 / 反复否定（「不代表」「不承诺」「不能」）：集中在 `README.md` §8-10、`PROJECT_BRIEF.md` §9、`METHODOLOGY.md` §6、`REPRODUCIBILITY.md` §2 —— 四份文档存在**重复的局限性/边界陈述**，建议合并到单一「边界」来源，其余引用。
- 内部审核语气 / 作品集求职导向：`index.html` §能力映射（role-grid，含 Riot/Ubisoft 招聘链接）偏求职导向，与「偏评测的可核查分析案例」定位需再权衡。
- 过密双语标题 / 工程对象堆叠：README 各节「中文（English）」双语标题较密；文档大量出现 `final_evidence_table.csv`、`supporting_ids`、`needs_human_review` 等工程对象，面向普通读者的页面应弱化（页面本身已相对克制）。
- 「可以直接采信」/ 不真实的人工复核描述：见 §2，需降级。

## 5. Git worktree 与安全确认

- 使用**独立 Git worktree**：`C:\Users\magnussun\Desktop\PsyLens_Audit`，本地分支 `audit/evidence-chain-and-demo-local`，上游 `origin/audit/evidence-chain-and-demo`。
- 原目录 `C:\Users\magnussun\Desktop\PsyLens` 的 **15 个未追踪文件保持不变**（未移动/删除/修改/提交/stash/clean）。
- 审计 worktree 初始 `git status` 为空（干净）。
- 推送目标：`HEAD:audit/evidence-chain-and-demo`（不推 main、不建远程 local 分支、不建 PR）。
- 未修改：README、docs/index.html、docs/style.css、docs/files 历史数据、DOCX、scripts_public 原脚本、main。
- **未调用真实 API、未运行真实抓取、未读取/创建任何 Cookie/Token/Key。**

## 6. 交付物

- 脚本：`tools/audit_public_data.py`（离线/确定性/非零退出表示阻断；多候选感知、指标拆分）。
- 测试：`tests/test_public_data_audit.py`（25 项，全部通过；含多候选、歧义不分配平台、唯一命中才算 offset、两个 parent 指标、confidence/review 分离、不伪造 id、不出现「真实性已证明」）。
- 报告：`docs/audit/` 下 8 份审计 MD + `ID_MISMATCH_REPORT.csv`；另保留线上复核 `ONLINE_REVIEW_NOTES.md`（未修改）。
- 临时产物（`artifacts/audit/`，已 gitignore，不提交）：完整 JSON、逐行 linkage CSV、DOCX 比较 JSON、运行日志。

## 7. 审计脚本运行结果

- `python tools/audit_public_data.py` → 退出码 **1**（存在阻断项：`parent_semantic_linkage_rate=0.0`），摘要见 §1。
- `python -m pytest -q` → **25 passed**。
