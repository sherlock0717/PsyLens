# 评测方法（EVALUATION_METHOD）

> PsyLens 偏评测定位：不只展示"分析出了什么"，更评估"样本→证据→编码→洞察→建议"链条是否可靠。
> 指标定义见 `evaluation/metrics.yaml`，阈值与阻断级别见 `evaluation/thresholds.yaml`，失败类型见 `evaluation/failure_taxonomy.yaml`，计算器为 `tools/evaluate_v2.py`（离线、确定性）。

## 五组指标

- **A 数据完整性**：ID 唯一、证据文本可回溯、平台覆盖。
- **B 编码质量**：标签覆盖、不确定比例、非法标签、evidence_phrase 可定位、Agent 提案覆盖、人工复核覆盖。
- **C 洞察前置质量**：证据引用可解析、平台/时间窗覆盖、低支撑与单平台比例。
- **D 建议前置质量**：建议可回到洞察与证据、验证方法与预期效果覆盖、人工整理比例。
- **E 运行质量**：解析成功、可复现、manifest 完整、输出哈希一致。

## 判定规则

- 每个指标有阈值与级别（block/warn）。任一 block 未达标 → 整体 `evaluation_status=BLOCKED`。
- legacy 历史遗留指标（如 `parent_semantic_linkage_rate`）当前为 0，记为 **warn**（不重复阻断已 PASS 的 v2 迁移）。
- `human_review_coverage` 当前为 0（无真人复核），记为 warn。

## 口径纪律

- `evidence_text_match_rate` 只说明"证据文本可在公开样本中定位"，**不等于**采集/来源/标签/人工复核真实性。
- `proposal_confidence` 是机器置信度，不是证据强度，也不是人工确认。
- 面向页面用普通语言表述（如"每条展示证据都能回到对应的原始反馈"），工程字段保留在本文档与 README。
