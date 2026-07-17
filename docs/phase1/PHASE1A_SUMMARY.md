# Phase 1A 总结（PHASE1A_SUMMARY）

> PSYLENS-PHASE1A-001：稳定 ID、证据迁移与 B 站待处理队列。
> 只完成数据底座与迁移设计；未生成最终洞察/建议；未修改页面、README、DOCX 与历史公开数据。

## 0. 分层状态

| 维度 | 状态 |
| --- | --- |
| legacy_status | **BLOCKED**（历史证据链错位未修复） |
| v2_migration_status | **PASS**（迁移底座通过全部校验） |
| publication_readiness | **BLOCKED**（B 站证据仍在待处理队列，结构化洞察与行动建议尚未重建） |

> 不用单一 PASS 覆盖分层状态：v2 迁移部分已达标，但项目整体仍不具备公开发布条件。

## 1. 关键数量

| 项 | 值 |
| --- | --- |
| samples_v2 | 360 |
| 平台数量 | Bili 120 / NGA 120 / Tieba 120 |
| 自动迁移证据 | 695（唯一命中） |
| 歧义证据 | 2（`83_u2`、`96_u3`，pending_human_resolution） |
| Bili 队列覆盖样本 | 120 |
| Bili 候选单元 | 279 |
| review_status | 全部 `legacy_ai_label_unreviewed`（无「人工已复核」状态） |

## 2. ID 格式

- 样本：`<PLATFORM>_<0001-0120>`（`BILI_/NGA_/TIEBA_`，平台内出现顺序稳定）；
- 证据：`<sample_id>_U<两位序号>`（如 `NGA_0001_U02`）；
- 洞察 / 行动：仅格式规范 `INSIGHT_001` / `ACTION_001`，本阶段不生成实体（`deferred_until_evidence_rebuild`）。

## 3. 数据文件（data/v2/）

- `samples_v2.csv`、`evidence_v2.csv`、`ambiguous_evidence_queue.csv`、`bili_evidence_queue.csv`、`id_migration.csv`、`v2_manifest.json`。
- 生成脚本：`tools/build_v2_dataset.py`（确定性，复用审计器归一化/匹配口径）。
- 未写入 `docs/files/`；未覆盖任何历史公开结果。

## 4. manifest SHA-256（节选）

- source_commit：`371d245a0ce82ed5d980472147b49568525e2986`
- `samples_v2.csv`：`211f7012ff091f19d249ff5654b2d7b64253aeb35ca154982567563ddb06f8b8`
- `evidence_v2.csv`：`4616bceda1deb0e27d3b768557d080f0411b7f7d60d6b17a6366746480bee574`
- 审计已校验 manifest 全部哈希一致（`manifest_hash_ok = OK`）。

## 5. 审计命令与退出码

| 命令 | 退出码 | 含义 |
| --- | --- | --- |
| `python tools/audit_public_data.py --dataset legacy` | 1（非零） | legacy 仍 BLOCKED |
| `python tools/audit_public_data.py --dataset v2` | 0 | v2 迁移 PASS |
| `python tools/audit_public_data.py --dataset both` | 1（非零） | publication_readiness BLOCKED |

## 6. 边界与口径

- 「旧证据文本可在公开样本中定位」是迁移依据，**不等于**采集/来源/标签真实性或人工复核；
- legacy AI 标签**尚未人工复核**；`confidence` 是模型置信度，非证据强度；
- B 站候选单元为**待处理队列**，非最终证据，无最终机制标签；
- 结构化洞察与行动建议**尚未重建**；
- v2 **尚不具备公开发布条件**。

## 7. 后续（Phase 1B+ 建议，本阶段不执行）

1. 人工确认 2 条歧义证据（或作废过短单元）；
2. 复核并标注 B 站候选单元，使证据层覆盖三平台；
3. 建立真实人工复核日志与 override 记录；
4. 在稳定 ID 上重建结构化洞察与可回溯行动建议；
5. 数据与主张稳定后再更新页面、README 与正式 DOCX。
