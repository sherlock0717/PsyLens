# 稳定 ID 方案（ID_SCHEME）

> PSYLENS-PHASE1A-001 → 002（生成器与稳定性加固）。采用方案 B：带平台前缀、平台内稳定编号。本阶段仅建立数据底座，v2 尚不用于公开页面。
>
> **稳定性边界**：这里的「稳定」指针对**当前冻结的 legacy 样本集合与迁移表**——只要 legacy clean 数据不变，无论输入行如何重排，`legacy_clean_id -> sample_id` 的映射都保持不变。它**不宣称**重新采集或重新编号后仍自动稳定；未来若数据集变化，需重新冻结并更新迁移表。

## 1. 样本 ID

格式：`<PLATFORM>_<四位序号>`

| 平台 | 前缀 | 范围 |
| --- | --- | --- |
| B 站 | `BILI` | `BILI_0001` ～ `BILI_0120` |
| NGA | `NGA` | `NGA_0001` ～ `NGA_0120` |
| 贴吧 | `TIEBA` | `TIEBA_0001` ～ `TIEBA_0120` |

编号规则：

- 按 `platform_source + numeric legacy_clean_id` 的**稳定排序**编号，**不依赖 clean CSV 当前遍历顺序**；
- 每个平台独立从 `0001` 开始；
- **不依赖全局行号**（全局行号在未来合并/排序时可能变化）；
- 对冻结的 legacy 样本集合，输入行重排不改变 `legacy_clean_id -> sample_id` 映射（有测试 `test_v2_sample_id_mapping_stable_under_shuffle` 保障）。

## 2. 证据 ID

格式：`<sample_id>_U<两位单元序号>`

示例：`NGA_0001_U01`、`NGA_0001_U02`、`TIEBA_0037_U04`。

- `unit_index` **保留 legacy evidence id 的 `_uN` 后缀**（如 `83_u1 -> NGA_0083_U01`），不使用压缩后的连续计数器重新编号，避免未来补回歧义单元时既有 ID 漂移；
- 生成时检测同一 `sample_id + unit_index` 冲突，冲突即 BLOCKED，不静默重新编号；
- `evidence_id` 的平台前缀必须与其 `sample_id` 一致。

## 3. 洞察 / 行动 ID（本阶段仅格式规范，不生成实体）

- 洞察：`INSIGHT_001`
- 行动：`ACTION_001`

结构化洞察与行动建议在证据层重建完成前不生成实体（见迁移表标记 `deferred_until_evidence_rebuild`）。

## 4. 与 legacy ID 的关系

- legacy clean id（如 `1`、`121`）→ sample_id（如 `BILI_0001`、`NGA_0001`）；
- legacy evidence id（如 `1_u2`）→ evidence_id（如 `NGA_0001_U02`），仅对**唯一命中**的证据；
- 完整对照见 `data/v2/id_migration.csv`。

> 说明：legacy evidence 的 `parent_id` 与公开 clean CSV 的 id 空间错位（见 Phase 0 审计）。v2 通过「unit_text 唯一定位到真实样本」来重建正确关联，而非机械加 120。
