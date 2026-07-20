# PsyLens 公开数据

本目录提供用于页面展示和离线复现的脱敏数据。

## 文件

- `samples_public.csv`：360 条完整样本；
- `evidence_public.csv`：927 条证据单元；
- `migration_history.json`：公开 schema 迁移操作、数量与保持不变的字段；
- `public_manifest.json`：字段、行数、转换记录和 SHA-256；
- `README.md`：字段与解释口径。

## 样本字段

| 字段 | 含义 |
| --- | --- |
| `sample_id` | 稳定样本编号 |
| `platform_source` | 平台类别 |
| `platform_sequence` | 平台内顺序 |
| `window_tag` | 时间窗标签 |
| `theme_bucket` | 平衡抽样时使用的粗粒度分层 |
| `reply_type` | 主帖上下文或近期回复 |
| `date` | 可获得时记录的日期 |
| `public_text` | 公开脱敏文本 |
| `migration_status` | 数据迁移状态 |

## 证据字段

| 字段 | 含义 |
| --- | --- |
| `evidence_id` | 稳定证据编号 |
| `sample_id` | 对应父样本 |
| `platform_source` | 平台类别 |
| `unit_index` | 样本内部证据顺序 |
| `unit_text` | 可在父样本中定位的证据文本 |
| `surface_topic` | 表层话题 |
| `mechanism_label` | 体验机制 |
| `label_source` | 编码来源 |
| `review_status` | 编码流程状态 |
| `analysis_inclusion_status` | 证据纳入状态 |

## Schema 迁移

公开版 2.0 完成两项字段规范化：

- 移除 360 条样本中与 `public_text` 内容相同的冗余 `raw_text` 列；
- 将 47 条空的 `surface_topic` 统一写为 `other_uncertain`。

迁移不改变样本编号、证据编号、公开文本、证据文本、父样本关系和平台字段。详细记录见 `migration_history.json`。

## 两种“不确定”

- `mechanism_label=uncertain`：文本不足以明确判断体验机制；
- `analysis_inclusion_status=included_flagged_uncertain`：证据仍然保留，但纳入时存在上下文或解释风险。

二者属于不同字段，统计时需要分开报告。当前前者为 486 条，后者为 163 条。

## 解释口径

- 三个平台各 120 条属于等额抽样设计，不能代表平台真实讨论量；
- 证据数量受样本文本长度和切分粒度影响；
- `theme_bucket` 用于样本覆盖与抽样，不等同于证据层 `surface_topic`；
- 当前编码包含历史 AI 结果和离线规则提案，适合方法审计与探索性分析；
- 240 条样本日期为空，涉及时间趋势的分析需排除这些记录或补充日期。

详细方法见：

- `docs/methodology/DATA_CLEANING_AND_CODING.md`
- `docs/methodology/PSYCHOLOGY_FRAMEWORK.md`
- `docs/evaluation/EVALUATION_METHOD.md`
