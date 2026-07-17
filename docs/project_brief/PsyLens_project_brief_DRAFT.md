# PsyLens 项目说明（统一底稿 · DRAFT）

> 本文件是统一项目说明的 **Markdown 底稿**，以 legacy v4 为改写基础，内容与新 README 和展示页口径一致。
> 正式 DOCX（`docs/files/PsyLens_project_brief.docx`）与旧版 v3/v4 的归档属用户决策 **D-009**，本阶段不生成正式 DOCX、不移动/删除旧版。

## 1. 定位

PsyLens 是一个**偏评测的可核查社区反馈分析案例**：把公开社区反馈整理成可回溯证据，并评估"样本 → 证据 → 编码 → 洞察 → 产品假设"链条的可靠性。

## 2. 当前案例与数据

- 三平台公开反馈，360 条样本（每平台 120）。
- 两层数据：样本层与证据层；证据数量不等于样本数量。
- legacy 与 v2：legacy 为历史中间产物；v2 用稳定编号重建，695 条唯一命中证据已迁移。

## 3. v2 证据链

- 稳定平台前缀 ID（`BILI_/NGA_/TIEBA_`），证据 ID 保留 legacy `_uN`；
- provisional 三平台证据层（legacy 迁移 + B 站 Agent 提案）；
- 证据文本可在公开样本中定位（不等于采集/来源真实性）。

## 4. Agent 提案与人工复核的区别

- B 站标签为 **Agent 提案**（`agent_proposed_unreviewed`），非人工复核；
- 当前人工复核覆盖为 0；不得表述为"已人工复核 / 已验证 / 可直接采信"。

## 5. 离线 Demo

- `python tools/run_demo.py`：离线、确定性、mock provider；
- 生成证据、草稿洞察、待验证产品假设、评测报告。

## 6. 评测指标

- 五组：数据完整性、编码质量、洞察前置、建议前置、运行质量；
- 定义/阈值见 `evaluation/`；当前 `evaluation_status=PASS`（1 项 legacy 警告）。

## 7. 历史观察

legacy 分析得到的观察作为历史观察保留，正用 v2 证据层复核，尚未作为当前结论。

## 8. 待验证产品假设

由高支持结构化洞察生成的草稿假设，含预期效果、验证方法、成功指标；默认不公开，需实验验证。

## 9. 数据与隐私边界

- 公开层不展示原始 URL；完整数据下载默认不开放；
- 示例数据脱敏；不做大规模再分发。

## 10. 许可

Copyright © 2026 Sherlock0717. All rights reserved.

---

> 生成正式 `PsyLens_project_brief.docx` 并归档 v3/v4，属决策 D-009，等待用户确认后执行。
