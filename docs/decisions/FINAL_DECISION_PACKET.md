# 最终决策包（FINAL_DECISION_PACKET）

> 集中列出所有仍需用户决定的问题。工程实现已完成，公开发布待以下决策。
> 回复格式示例：`D-001：选择 A`。机器可读副本见 `data/decisions/decision_register.json`。

## 状态总览

- engineering_completion = COMPLETE
- public_release_readiness = PENDING_USER_DECISIONS
- main_merge_status = NOT_STARTED
- pages_deployment_status = NOT_STARTED

---

## D-001 完整数据是否在页面提供下载

- 当前：页面不提供下载（`show_full_data_download=false`）。
- **A. 继续不提供完整数据下载（推荐）**
- B. 页面提供脱敏数据下载
- C. 页面提供完整数据下载
- 影响：仅下载入口可见性。需改：`docs/index.html`、`showcase.json`。

## D-002 原始 source_url 是否继续保留和公开

- 当前：底层保留、公开层全部隐藏（`show_raw_urls=false`）。
- **A. 底层保留、公开层隐藏（推荐）**
- B. 公开层展示脱敏 URL
- C. 公开层展示完整 URL
- 影响：`showcase.json`、Demo、页面。

## D-003 两条歧义证据（83_u2 / 96_u3）

- 当前：`pending_human_resolution`，不进入统计与洞察。
- **A. keep_pending 或 exclude_as_too_short（推荐排除）**
- B. assign_to_candidate（需指定）
- C. merge_with_previous_unit
- 影响：证据分母、平台覆盖。见 `docs/review/AMBIGUOUS_EVIDENCE_DECISION_PACKET.md`。

## D-004 B 站 Agent 标签是否获人工认可

- 当前：`agent_proposed_unreviewed`（279 条）。
- **A. 保持提案状态（推荐），待人工复核**
- B. 部分人工确认
- C. 全量人工确认
- 影响：`human_review_coverage`、公开结论口径。

## D-005 草稿结构化洞察是否发布

- 当前：`hidden_pending_review`（28 条，`show_draft_v2_insights=false`）。
- **A. 隐藏，仅展示历史观察与评测状态（推荐）**
- B. 标注草稿后展示
- C. 作为正式结论展示
- 影响：`showcase.json`、页面。

## D-006 草稿行动建议是否发布

- 当前：`hidden_pending_review`（6 条，`show_draft_action_hypotheses=false`）。
- **A. 隐藏（推荐）**
- B. 标注"待验证产品假设"后展示
- C. 作为正式建议展示

## D-007 Pages 最终部署方式

- 当前：分支内已准备 `.github/workflows/pages.yml`，未改线上设置。
- **A. 保持准备状态，由线上复核决定（推荐）**
- B. 立即迁移 Pages 源
- C. 手动部署

## D-008 是否合并 main

- 当前：所有工作在 `phase1/rebuild-evidence-and-demo`。
- **A. 暂不合并，先复核（推荐）**
- B. 合并 main

## D-009 是否公开正式 DOCX

- 当前：已生成统一 Markdown 底稿 `docs/project_brief/PsyLens_project_brief_DRAFT.md`；未生成正式 DOCX、未移动 v3/v4。
- **A. 确认后生成正式 `PsyLens_project_brief.docx` 并归档 v3/v4（推荐）**
- B. 立即公开正式 DOCX

## D-010 是否进一步做真实模型运行

- 当前：Demo 默认离线 mock；真实 provider 仅接口。
- **A. 保持离线 mock（推荐）**
- B. 用户显式配置后本地运行真实 provider
- C. CI 中运行（不建议）

---

## 推荐决策摘要

全部推荐 **A**：保守、可逆、不改动线上、不冒充正式发布。用户确认后再执行发布、合并、部署与 DOCX 归档等不可逆操作。
