# 延期决策登记（DEFERRED_DECISIONS）

> 本任务采用「集中决策」机制。除安全性与数据破坏风险外，所有产品、文案、标签或发布选择不中途询问，统一在此登记并以最保守、可逆的 `safe_default` 继续工作。
> 最终汇总见 `docs/decisions/FINAL_DECISION_PACKET.md`；机器可读副本见 `data/decisions/decision_register.json`。

| 字段 | 含义 |
| --- | --- |
| decision_id | 决策编号（D-001…） |
| title | 标题 |
| background | 背景 |
| options | 候选选项 |
| recommended_option | 推荐选项 |
| safe_default | 未决前采用的安全默认 |
| affected_files | 影响文件 |
| affected_metrics | 影响指标 |
| publication_effect | 对公开发布的影响 |
| status | 状态（统一先写 deferred） |
| final_decision | 用户最终决定（待填） |

---

## D-001 完整数据是否在页面提供下载

- background：下载 CSV 含精确来源信息，是否在公开页面提供下载需用户裁定。
- options：A. 页面不提供完整数据下载（推荐）；B. 页面提供脱敏数据下载；C. 页面提供完整数据下载。
- recommended_option：A
- safe_default：`show_full_data_download = false`。文件保留在工作分支；页面不展示下载按钮；README 不把完整数据作为主要入口；只公开脱敏示例数据。
- affected_files：`docs/index.html`、`docs/assets/data/showcase.json`、`README.md`
- affected_metrics：无（仅展示层）
- publication_effect：不影响发布，仅影响下载入口可见性
- status：deferred
- final_decision：（待用户确认）

## D-002 原始 source_url 是否继续保留和公开

- background：数据底层含真实 URL，是否在公开页面/JSON 展示需裁定。
- options：A. 底层保留、公开层全部隐藏（推荐）；B. 公开层展示脱敏 URL；C. 公开层展示完整 URL。
- recommended_option：A
- safe_default：数据底层保留原字段；展示页不显示；Demo 数据不含真实 URL；公开页面 JSON 不写入真实 URL。
- affected_files：`docs/assets/data/showcase.json`、`demo/examples/*`、`docs/index.html`
- affected_metrics：`source_url_coverage`（仅底层统计）
- publication_effect：不影响发布
- status：deferred
- final_decision：（待用户确认）

## D-003 两条歧义证据如何处理

- background：`83_u2`（「没啥用」）与 `96_u3`（「没了」）为极短文本，多候选来源不确定。
- options：A. keep_pending（推荐）；B. exclude_as_too_short；C. assign_to_candidate；D. merge_with_previous_unit。
- recommended_option：A（保持 pending，等待人工确认）
- safe_default：`resolution_status = pending_human_resolution`。不自动定案；不进入正式证据统计；不进入结构化洞察；保留候选与上下文。
- affected_files：`data/v2/ambiguous_evidence_queue.csv`、`data/v2/evidence_exclusion_log.csv`
- affected_metrics：证据分母、平台覆盖
- publication_effect：不影响发布（两条不进入公开指标）
- status：deferred
- final_decision：（待用户确认）

## D-004 B 站离线规则基线标签是否获人工认可

- background：B 站 279 候选单元由本地关键词规则基线依据 codebook 生成初步提案（非人工/模型语义复核），尚未人工复核。
- options：A. 保持 rule_based_proposed_unreviewed（推荐）；B. 部分人工确认；C. 全量人工确认。
- recommended_option：A
- safe_default：`review_status = rule_based_proposed_unreviewed`。可进入草稿分析；不得称为人工复核；不进入正式公开结论；页面默认不展示为已确认结果。
- affected_files：`data/v2/rule_based_label_proposals.csv`、`data/v2/evidence_provisional_v2.csv`
- affected_metrics：`human_review_coverage`、`label_completion_rate`
- publication_effect：草稿层，不作为已确认结论发布
- status：deferred
- final_decision：（待用户确认）

## D-005 草稿结构化洞察是否发布

- background：v2 证据层上重建的结构化洞察为 Agent 草稿。
- options：A. 隐藏，仅展示历史观察与评测状态（推荐）；B. 标注草稿后展示；C. 作为正式结论展示。
- recommended_option：A
- safe_default：`show_draft_v2_insights = false`。页面可展示历史分析观察、当前评测状态、证据链案例、Demo 运行结果。
- affected_files：`docs/assets/data/showcase.json`、`docs/index.html`
- affected_metrics：无
- publication_effect：草稿默认隐藏
- status：deferred
- final_decision：（待用户确认）

## D-006 草稿行动建议是否发布

- background：可追溯产品假设为 Agent 草稿，未经实验验证。
- options：A. 隐藏（推荐）；B. 标注「待验证产品假设」后展示；C. 作为正式建议展示。
- recommended_option：A
- safe_default：`show_draft_action_hypotheses = false`。
- affected_files：`docs/assets/data/showcase.json`、`docs/index.html`
- affected_metrics：无
- publication_effect：草稿默认隐藏
- status：deferred
- final_decision：（待用户确认）

## D-007 Pages 最终部署方式

- background：需要一套 GitHub Pages 部署 workflow，但不改动线上设置。
- options：A. 仅在分支内准备 workflow，线上由复核决定（推荐）；B. 立即迁移 Pages 源；C. 手动部署。
- recommended_option：A
- safe_default：在分支内准备 `.github/workflows/pages.yml`；不修改线上 Pages 设置；不合并 main；最终由线上复核决定。
- affected_files：`.github/workflows/pages.yml`
- affected_metrics：无
- publication_effect：不改动线上 Pages
- status：deferred
- final_decision：（待用户确认）

## D-008 是否合并 main

- background：所有工作在 `phase1/rebuild-evidence-and-demo`，是否合并 main 需裁定。
- options：A. 暂不合并，等待复核（推荐）；B. 合并 main。
- recommended_option：A
- safe_default：不合并 main。
- affected_files：无
- publication_effect：main 不变
- status：deferred
- final_decision：（待用户确认）

## D-009 是否公开正式 DOCX

- background：以 v4 为底稿的统一项目说明，是否作为正式版公开。
- options：A. 生成 Markdown 底稿并归档旧版，DOCX 待确认（推荐）；B. 立即公开正式 DOCX。
- recommended_option：A
- safe_default：生成正式底稿（Markdown 或安全生成的 DOCX），旧 v3/v4 归档；页面/README 不再链接旧版本。
- affected_files：`docs/files/PsyLens_project_brief.docx`（或 Markdown 底稿）、`docs/files/archive/**`
- publication_effect：正式入口只保留一份
- status：deferred
- final_decision：（待用户确认）

## D-010 是否进一步做真实模型运行

- background：Demo 默认离线、mock provider；是否接入真实模型运行需裁定。
- options：A. 保持离线 mock（推荐）；B. 用户显式配置后本地运行真实 provider；C. CI 中运行（不允许）。
- recommended_option：A
- safe_default：Demo 默认离线；真实 provider 仅提供接口，不在 CI 运行。
- affected_files：`demo/src/providers.py`、`demo/config/demo.yaml`
- publication_effect：无
- status：deferred
- final_decision：（待用户确认）
