# 受限数据文件清单（RESTRICTED_DATA_FILES）

> 本清单列出**含来源链接或身份定位字段**的内部数据文件。这些文件仅用于内部审计与迁移可核查性，
> **不进入公开发布合并范围**（默认不合并进未来 main 的发布集合）。公开发布只使用 `data/public/**`。

## 含 source_url / 内部标题的文件

| 文件 | 敏感字段 | 处理 |
| --- | --- | --- |
| `data/v2/samples_v2.csv` | `source_url`、`thread_or_video_title` | 内部保留；公开用 `data/public/samples_public.csv`（已移除） |
| `docs/files/input_feedback_phase2_multiplatform_clean.csv` | 原始来源字段 | legacy 历史中间产物；不作为公开入口 |
| `docs/files/final_evidence_table.csv` | 可能含来源引用 | legacy 历史中间产物；不作为公开入口 |

## 说明

1. **历史 Git 提交**：上述内部文件已存在于当前工作分支与历史提交中，删除当前文件**不能**消除历史可访问性。
2. **未执行历史重写**：本任务不重写 Git 历史、不 force push。是否对历史进行清理属延期决策（见 `docs/decisions/FINAL_DECISION_PACKET.md` D-001 / D-002）。
3. **发布合并范围**：推荐未来 main 只公开 `data/public/**`；含 `source_url` 的内部 v2 文件不进入最终发布合并范围。
4. **公开副本**：`data/public/samples_public.csv`、`data/public/evidence_public.csv` 已移除来源链接与身份定位字段，并对文本做脱敏，`public_manifest.json` 记录 SHA-256 与脱敏策略。
