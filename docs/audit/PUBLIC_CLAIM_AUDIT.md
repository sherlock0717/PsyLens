# 页面主张审计（PUBLIC_CLAIM_AUDIT）

> 检查 `docs/index.html`、`README.md`、`PROJECT_BRIEF.md`。所有 verified/contradicted 结论均从公开文件重算，未仅凭「页面写了来源」判定通过。
> claim_type：count / distribution / comparison / mechanism_interpretation / cross_platform_claim / human_review_claim / reproducibility_claim / action_hypothesis / privacy_claim。
> verification_status：verified / partially_verified / unsupported / contradicted / unclear。

## 1. 主张核对表

| claim_id | 位置 | 主张 | 类型 | 来源文件 / 指标 | 状态 | 备注 |
| --- | --- | --- | --- | --- | --- | --- |
| C01 | index.html L25/69; README L27 | 360 整洁样本 | count | clean CSV 行数 | verified | 实测 360 |
| C02 | index.html L26/73; README L28 | 697 证据单元 | count | evidence 行数 | verified | 实测 697 |
| C03 | index.html L27/77; README L29 | 19 验证洞察 | count | insights JSONL 行数 | verified | 实测 19 |
| C04 | index.html L201; PROJECT_BRIEF L29 | 三平台各 120 | distribution | clean platform_source | verified | Bili/NGA/Tieba=120/120/120 |
| C05 | index.md L62-63 | 时间窗 w1=260 / w2=100 | distribution | clean window_tag | verified | 实测一致 |
| C06 | index.html L272/610 | 玩法/机制样本主轴 236 | count | theme_bucket=balance_mechanic | verified | 实测 236 |
| C07 | index.html L612 | 证据层 balance=192 | count | surface_topic=balance | verified | 实测 192 |
| C08 | index.html L301/593 | 胜任受挫 268 | count | mechanism=competence_frustration | verified | 实测 268 |
| C09 | index.html L306/599/617 | 公平威胁 72 | count | mechanism=fairness_threat | verified | 实测 72 |
| C10 | index.html L295/602 | 剔除「暂不确定」336 | count | mechanism=uncertain | verified | 实测 336 |
| C11 | index.html L631 | 玩法/机制三平台 84·81·71 | distribution | theme_bucket=balance_mechanic 按平台 | verified | Bili84/NGA81/Tieba71（样本层） |
| C12 | index.html L624 | 放大器 10·8·3 | distribution | trust_communication_gap/belonging_drop/norm_safety_risk | verified | 实测 10/8/3 |
| C13 | index.html L654 | 高置信主线「约 8 条」 | count | confidence / needs_human_review | **partially_verified** | 见 §5：`confidence=high`=**7**、`needs_human_review=false`=**8**、交集=**7**；「8」对应的是模型 review 标记而非置信度，且不等于人工确认 |
| C14 | index.html L659/707 | 需复核补充「约 11 条」 | count | needs_human_review=true | partially_verified | `needs_human_review=true`=11（模型字段，非人工判定「需复核」的结论） |
| C15 | index.html L563 | 示例 `1_u2` 来源 parent_id=1，**平台 B 站** | mechanism_interpretation | evidence 1_u2 → clean | **contradicted** | 1_u2 唯一命中 clean id=121（candidate_count=1），平台 **NGA**；见 §2 |
| C16 | index.html L648/655 | 高置信主线「可以直接采信」 | human_review_claim | needs_human_review / 复核记录 | **unsupported** | needs_human_review 是模型字段，非人工确认；无复核记录，见 §3 |
| C17 | index.html L588 | 机制标签「由 AI 辅助并**经人工复核**」 | human_review_claim | 仓库复核记录 | **unsupported** | 仓库无任何逐行/抽样人工复核日志 |
| C18 | index.html L630-632 | 「三平台表达不同，主线一致」 | cross_platform_claim | evidence 实际出处平台 | **partially_verified** | 样本层为三平台；但**证据层实际只覆盖 NGA+Tieba**，机制主线（268/72）不含 Bili 证据 |
| C19 | index.html L757-784 | 页面四张行动卡（降低理解成本等） | action_hypothesis | 05_action_matrix.json | partially_verified | 页面已如实注明「人工整理、与 JSON 非一一对应」；但无 insight/evidence 级可追溯字段 |
| C20 | README L114-117; REPRODUCIBILITY | 公开仓库不承诺一键复现 | reproducibility_claim | 仓库缺 prompts/config/依赖 | verified | 与实际一致（诚实边界） |
| C21 | index.html L394; README L133 | 三平台各 120 为平衡样本，不代表自然声量 | distribution | — | verified | 表述准确 |
| C22 | 页面不展示原始 URL | — | privacy_claim | index.html | verified | 页面未出现原始 URL；下载 CSV 含 URL（见隐私报告） |

## 2. 页面示例证据 `1_u2` —— 未闭合（contradicted）

页面 L563：「证据编号 `1_u2`（来源样本 `parent_id=1`，平台 **B 站**），可在证据表与验证洞察文件中逐项核对。」

实测：

- `1_u2` 存在于证据表，`mechanism_label=competence_frustration`，`confidence=high`，`surface_topic=balance`。
- `1_u2` 被 line 1 洞察（balance×competence_frustration）引用 —— 该半环成立。
- 但 `unit_text`（「说真的，你选就选了，让个金，还要让 3000 的经济去出个……心之钢。」）**不在** clean id=1（Bili，坦克海克斯话题）的 `raw_text` 中。
- 该文本在整洁样本中**唯一命中**（candidate_count=1）于 **clean id=121（NGA）**。
- 因此页面「parent_id=1、平台 B 站」的溯源**指向错误行、错误平台**。`page_claim_correct = False`，`chain_closed = False`。

**这是审计阻断项之一（页面示例证据链错误）。**

## 3. 「可以直接采信 / 经人工复核」—— unsupported

- 页面多处（L588 机制标签「经人工复核」、L648/655「可以直接采信」）暗示已完成人工复核。
- 仓库中**不存在**任何人工复核证据：无逐行复核日志、无复核前后标签、无复核人/复核类型、无 human_override 记录。唯一相关字段是 `04_validated_insights.jsonl` 的模型输出 `needs_human_review`，以及 pipeline 中默认 `needs_human_review=false` 的模型返回。
- 结论：**不得将模型 `needs_human_review=false` 解释为「人工已复核、可直接采信」**。相关表述需降级（详见 `PHASE0_SUMMARY.md` §人工复核）。

## 4. 需降级 / 修正的公开表述（本阶段仅列出，不改文件）

1. L563 `1_u2` 平台由「B 站」改为「NGA」，并修复 parent_id 对齐（阻断项）。
2. L588「经人工复核」→ 改为「AI 辅助标注，尚未完成系统人工复核」或补真实复核记录后再用。
3. L648/655「可以直接采信」→ 「高频、跨证据稳定，但仍需人工确认」。
4. L630-632「三平台……主线一致」→ 注明机制主线证据层实际仅覆盖 NGA+Tieba。
5. 高置信主线中多条实际为**单平台**支撑，不宜表述为跨平台共识。
6. L654「高置信主线约 8 条」→ 改为「置信度为 high 的洞察 7 条」，并与「模型标记 needs_human_review=false 的 8 条」区分表述，避免混淆两个字段。

## 5. C13 重新判定：confidence 与 needs_human_review 是两个字段

页面 L654「高置信主线 · 约 8 条」。据实重算（`tools/audit_public_data.py`）：

| 口径 | 数量 | 行号 |
| --- | --- | --- |
| `confidence == high` 的洞察 | **7** | 1, 2, 3, 6, 10, 11, 13 |
| `needs_human_review == false`（模型输出字段） | **8** | 1, 2, 3, 6, 10, 11, 13, 16 |
| 两者交集（high 且 no_review_flag） | **7** | 1, 2, 3, 6, 10, 11, 13 |

- 页面的「约 8 条」实际对应的是**模型字段 `needs_human_review=false` 的数量（8）**，而不是「高置信度」的数量（7；line 16 为 `confidence=medium`）。
- **不得仅因 `needs_human_review=false` 有 8 条即判 verified**：该字段是**模型输出**，既不等于 confidence，也不等于人工确认。
- 结合「可以直接采信」这一人工复核暗示无任何复核记录支撑（§3），**C13 判定为 `partially_verified`**：计数口径可核（7 或 8，取决于字段），但「高置信 = 可直接采信」的结论**unsupported**。
