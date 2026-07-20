# 最终决策包（FINAL_DECISION_PACKET）

> 集中列出所有仍需用户决定的问题。工程实现已完成，公开发布待以下决策。
> 回复格式示例：`D-001：选择 A`。机器可读副本见 `data/decisions/decision_register.json`。

## 状态总览

- engineering_completion = COMPLETE_LOCALLY
- remote_ci_status = NOT_VERIFIED（本地无 GitHub CLI/网络凭据，推送触发 CI，需线上查看）
- public_release_readiness = PENDING_USER_DECISIONS
- main_merge_status = NOT_STARTED
- pages_deployment_status = NOT_STARTED

---

## D-001 含来源字段的内部数据是否继续保留在未来 main

- 当前：已生成不含来源字段的 `data/public/**`；展示页不提供下载入口。
- **A. 未来 main 只合并 data/public（推荐）**
- B. 同时合并含来源字段的 v2 内部文件
- C. 合并前先做历史清理
- 影响：发布合并范围。见 `data/internal_manifest/RESTRICTED_DATA_FILES.md`。

## D-002 历史提交中的来源 URL 是否需要后续单独清理

- 当前：未重写历史；公开层与 data/public 无来源 URL；历史提交仍可能含旧数据。
- **A. 暂不重写历史，发布只用 data/public（推荐）**
- B. 后续单独执行历史清理
- C. 接受历史中保留来源字段
- 影响：是否清理历史。见 `FINAL_PRIVACY_AUDIT.md`。

## D-003 两条歧义证据（83_u2 / 96_u3）

- 当前：`pending_human_resolution`，不进入统计与洞察。
- **A. keep_pending 或 exclude_as_too_short（推荐排除）**
- B. assign_to_candidate（需指定）
- C. merge_with_previous_unit
- 影响：证据分母、平台覆盖。见 `docs/review/AMBIGUOUS_EVIDENCE_DECISION_PACKET.md`。

## D-004 B 站离线规则基线标签是否获人工认可

- 当前：`rule_based_proposed_unreviewed`（279 条；关键词规则基线，非人工/模型语义复核）。
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

## D-009 正式 DOCX 是否在页面突出展示

- 当前：正式 `docs/files/PsyLens_project_brief.docx` **已生成**，v3/v4 已归档至 `archive/project_brief_legacy/`，README/页面仅链接这一份（不再是"是否生成"的决策）。
- **A. 保持为文件入口链接，不在页面顶部突出展示（推荐）**
- B. 在页面显著位置突出展示项目说明 DOCX
- 影响：仅页面呈现方式；正式入口已完成。

## D-010 是否进一步做真实模型运行

- 当前：Demo 默认离线 mock；真实 provider 仅接口。
- **A. 保持离线 mock（推荐）**
- B. 用户显式配置后本地运行真实 provider
- C. CI 中运行（不建议）

---

## 推荐决策摘要

全部推荐 **A**：保守、可逆、不改动线上、不冒充正式发布。用户确认后再执行发布、合并、部署与 DOCX 归档等不可逆操作。
