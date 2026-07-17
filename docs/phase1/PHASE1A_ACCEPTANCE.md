# Phase 1A 正式验收（PHASE1A_ACCEPTANCE）

> 本文件记录 Phase 1A（含 001/002/003）的工程验收结论。数据迁移方向通过，但整体仍不具备公开发布条件。

## 1. Phase 1A-003 九项验收

| # | 验收项 | 状态 |
| --- | --- | --- |
| 1 | `write_linkage_csv` 恢复为模块级可调用函数 | 通过 |
| 2 | `--csv-out` smoke test（生成 697 行、列完整、退出码 1、无 NameError） | 通过 |
| 3 | `--mismatch-out` smoke test（文件生成、退出码 1） | 通过 |
| 4 | `--json-out`（v2）smoke test（JSON 生成、退出码 0、`v2_migration_status=PASS`） | 通过 |
| 5 | `source_data_commit` 精确校验（等于 `371d245…`，错误值 BLOCKED） | 通过 |
| 6 | `source_files` 精确校验（键集合 + 路径值精确等值） | 通过 |
| 7 | `unit_index` 不变量进入 `run_v2_audit`（篡改即 BLOCKED） | 通过 |
| 8 | pytest 不修改 tracked `data/v2/`（前后哈希一致） | 通过 |
| 9 | legacy / v2 / both 退出码 `1 / 0 / 1` | 通过 |

## 2. 分层状态

| 维度 | 状态 |
| --- | --- |
| legacy_status | BLOCKED（历史证据链错位未修复） |
| v2_migration_status | PASS（迁移底座通过全部校验） |
| provisional_evidence_status | 尚未建立（Phase E 建立后更新） |
| human_review_status | NOT_STARTED |
| publication_readiness | BLOCKED |

## 3. 数据迁移结论

- 360 条样本建立稳定平台前缀 ID（`BILI_/NGA_/TIEBA_`）；
- 695 条唯一命中 legacy 证据完成迁移（`unit_index` 保留 legacy `_uN` 后缀）；
- 2 条歧义证据隔离，`pending_human_resolution`；
- B 站 120 样本、279 条候选单元进入待处理队列。

## 4. 未开始 / 仍待事项

- **未开始真实人工复核**：`human_review_log.csv` 仅记录 system_migration 事件，无 `reviewer_type=human`；
- **B 站仍处于候选与 Agent 提案阶段**：所有 B 站标签为 `agent_proposed_unreviewed`，不得称为人工复核；
- 结构化洞察与行动建议仅为 Agent 草稿，默认隐藏；
- `publication_readiness` 仍 BLOCKED，公开发布须等待用户决策（见 `docs/decisions/DEFERRED_DECISIONS.md`）。

## 5. 结论

Phase 1A 数据迁移基线**通过验收**。后续在此基线上建立编码规范、复核基础设施、评测框架、离线 Demo、公开展示与 CI，公开发布状态保持 `PENDING_USER_DECISIONS`。
