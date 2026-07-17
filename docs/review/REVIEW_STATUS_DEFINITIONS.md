# 复核状态定义（REVIEW_STATUS_DEFINITIONS）

> 统一定义证据、提案、洞察、建议在流水线中的复核状态。关键原则：**Agent 提案不等于人工复核**，任何未经真实人工确认的标签都不得表述为「已人工复核 / 已验证 / 可直接采信」。

## 1. 证据 / 标签 review_status

| 状态 | 含义 | 可否作为公开结论 |
| --- | --- | --- |
| `legacy_ai_label_unreviewed` | legacy 阶段 AI 生成、未经系统人工复核的标签 | 否（草稿/历史观察） |
| `agent_proposed_unreviewed` | 本 Agent 依据 codebook 生成的提案，未经人工复核 | 否（草稿） |
| `human_reviewed` | 经真实人工逐条复核并确认 | 是（须有 `human_review_log` 记录） |
| `human_curated` | 经人工整理/编排（如行动建议） | 是（须有记录） |

> 当前阶段**不存在** `human_reviewed` / `human_curated` 的证据：`human_review_log.csv` 无 `reviewer_type=human` 记录。

## 2. 提案 proposal_status（agent_label_proposals）

| 状态 | 含义 |
| --- | --- |
| `agent_proposed_unreviewed` | Agent 提案，等待人工复核 |
| `human_accepted` | 人工采纳（待用户实际复核后才可能出现） |
| `human_rejected` | 人工否决 |
| `human_modified` | 人工修改后采纳 |

## 3. 洞察 / 建议 publication_status

| 状态 | 含义 |
| --- | --- |
| `hidden_pending_review` | 草稿，默认不在公开页面展示 |
| `visible_draft` | 标注为草稿后展示（须用户决策） |
| `published` | 正式发布（须用户决策） |

## 4. 歧义证据 resolution_status

| 状态 | 含义 |
| --- | --- |
| `pending_human_resolution` | 多候选、来源不确定，等待人工确认 |
| `resolved_assigned` | 人工指定候选 |
| `resolved_excluded` | 人工判定排除 |

## 5. 人工复核事件 reviewer_type

| 取值 | 含义 |
| --- | --- |
| `system_migration` | 系统迁移事件（非人工） |
| `agent` | Agent 操作（非人工复核） |
| `human` | 真实人工复核（当前不存在） |

> 严禁在无真实人工操作时写入 `reviewer_type=human`。
