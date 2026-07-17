# 最小评测框架提案（EVALUATION_FRAMEWORK_PROPOSAL）

> PsyLens 后续定位偏「可核查评测」而非只展示洞察。以下为最小可落地指标集。
> 每个指标给出：定义 / 分子 / 分母 / 阈值建议 / 阻断或警告 / 面向页面的普通语言解释。
> 本轮实测值取自 `tools/audit_public_data.py`（Phase 0 快照）。

## A. 数据完整性

| 指标 | 定义 | 分子 | 分母 | 阈值 | 级别 | 普通语言 | 本轮 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| sample_id_unique_rate | 样本 id 唯一比例 | 唯一 id 数 | 样本总数 | =1.0 | 阻断 | 每条反馈有唯一编号 | 1.0 |
| evidence_id_unique_rate | 证据 id 唯一比例 | 唯一 id 数 | 证据总数 | =1.0 | 阻断 | 每条证据有唯一编号 | 1.0 |
| parent_reference_exists_rate | `parent_id` 值能找到同编号 clean 行的比例 | 引用编号存在数 | 证据总数 | =1.0 | 警告 | 每条证据都写了一个存在的父样本编号 | **1.0** |
| parent_semantic_linkage_rate | `unit_text` 匹配**声明** parent 原文的比例 | 语义匹配数 | 证据总数 | ≥0.98 | 阻断 | 每条证据的文字确实来自它声明的那条原话 | **0.0** |
| evidence_text_locatable_rate | 证据文本能在整洁样本中**唯一**定位的比例 | 唯一命中数 | 证据总数 | ≥0.98 | 警告 | 证据文字能在公开样本中被唯一定位（≠证明采集/来源真实性） | 695/697≈0.997 |
| source_url_coverage | 有来源 URL 的样本比例 | url 非空 | 样本总数 | ≥0.95 | 警告 | 每条反馈都能点回原帖 | 1.0 |

## B. 编码质量

| 指标 | 定义 | 分子 | 分母 | 阈值 | 级别 | 普通语言 | 本轮 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| label_completion_rate | 机制/主题标签填充率 | 非空且合法标签数 | 证据总数 | ≥0.99 | 阻断 | 每条证据都完成了分类 | 1.0 |
| uncertain_rate | 机制为 uncertain 的比例 | uncertain 数 | 证据总数 | ≤0.55（警告线） | 警告 | 有多少证据「暂不确定」 | 336/697≈0.48 |
| invalid_label_rate | 非法标签比例 | 非法标签数 | 证据总数 | =0 | 阻断 | 没有超出定义的乱标签 | 0 |
| evidence_phrase_match_rate | evidence_phrase 是 unit_text 子串比例 | 命中数 | 非空 phrase 数 | ≥0.95 | 警告 | 关键短语确实出自该证据 | 695/696≈0.999 |
| human_review_coverage | 经人工复核的证据/洞察比例 | 有复核记录数 | 总数 | ≥目标值 | 警告 | 有多少结论真的人工看过 | **0（无记录）** |
| human_override_rate | 人工推翻模型标签比例 | 人工改动数 | 复核数 | 记录即可 | 警告 | 人工纠错了多少 | 无法计算（无复核） |

## C. 洞察质量

| 指标 | 定义 | 分子 | 分母 | 阈值 | 级别 | 普通语言 | 本轮 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| support_resolution_rate | supporting_ids 能在证据表找到的比例 | 命中 id 数 | supporting_ids 总数 | =1.0 | 阻断 | 每条洞察的引用都真实存在 | 1.0 |
| support_count | 每条洞察的支撑证据数 | — | — | 高置信≥5 | 警告 | 洞察背后有多少证据 | 高频洞察=8（上限截断） |
| platform_coverage | 洞察支撑覆盖的平台数（按实际出处） | — | — | 跨平台结论≥2 | 警告 | 结论是否被多平台支持 | 12/19 洞察为单平台 |
| time_window_coverage | 覆盖的时间窗数 | — | — | ≥1 | 警告 | 结论是否跨时间稳定 | 多为 w1 单窗 |
| low_support_claim_rate | 支撑<3 的洞察比例 | 低支撑洞察数 | 洞察总数 | ≤目标 | 警告 | 有多少结论证据偏薄 | 低频洞察偏多 |

## D. 建议质量

| 指标 | 定义 | 分子 | 分母 | 阈值 | 级别 | 普通语言 | 本轮 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| action_to_insight_linkage_rate | 建议能追到具体 insight 的比例 | 有 source_insight_ids 的建议 | 建议总数 | ≥0.9 | 警告 | 每条建议都说得清来自哪条洞察 | **0（无字段）** |
| action_to_evidence_linkage_rate | 建议能追到具体证据的比例 | 有 source_evidence_ids 的建议 | 建议总数 | ≥0.8 | 警告 | 每条建议都能落到玩家原话 | 0 |
| validation_plan_coverage | 有 validation_method 的建议比例 | 有验证方法数 | 建议总数 | ≥0.8 | 警告 | 每条建议怎么验证 | 0 |
| human_curated_rate | 有人工整理状态的建议比例 | review_status 非空数 | 建议总数 | ≥目标 | 警告 | 建议是否人工过目 | 0（JSON 无该字段） |

## E. 运行质量

| 指标 | 定义 | 分子 | 分母 | 阈值 | 级别 | 普通语言 | 本轮 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| parse_success_rate | 结果文件可解析比例 | 可解析文件/行 | 总数 | =1.0 | 阻断 | 文件都能被正常读取 | 1.0（JSONL 19/19、JSON ok） |
| stage_completion_rate | 流程各阶段产物齐备比例 | 齐备阶段数 | 阶段总数 | ≥目标 | 警告 | 每一步都留下了产物 | 结果层齐备；prompts/config 缺 |
| failure_type_counts | 各类失败计数 | — | — | 记录 | 警告 | 出了哪些类型的问题 | parent 错位=697 |
| repeatability_rate | 相同输入重复运行结果一致比例 | 一致运行数 | 重复次数 | =1.0 | 阻断 | 同样输入能跑出同样结果 | 1.0（审计脚本确定性，见测试） |
| output_manifest_completeness | 输出清单/manifest 完整度 | 有 manifest 项 | 应有项 | ≥目标 | 警告 | 有没有一份产物清单 | 无 run manifest |

## 使用说明

- **阻断（block）**：任一为真即判 BLOCKED；**警告（warn）**：记录并跟踪，不阻断。
- 本轮阻断触发：`parent_semantic_linkage_rate=0`（核心阻断），以及页面示例证据链错误。
- **口径纪律**：`evidence_text_locatable_rate` 只说明「文本可在公开样本中定位」，**不得**解读为「数据真实性 / 采集真实性 / 来源真实性 / 人工复核真实性」；`needs_human_review` 是模型字段，`human_review_coverage` 才反映真实人工复核。
- 指标可直接由 `tools/audit_public_data.py` 扩展输出，作为后续每次运行的评测卡。
