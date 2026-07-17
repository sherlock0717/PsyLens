# PsyLens

社区反馈分析与可靠性评测：把公开社区反馈整理成可回溯证据，并评估从编码到产品假设的每一步是否可靠。

- 展示页：`docs/index.html`（GitHub Pages）
- 当前状态：工程实现已完成；公开发布待用户决策（见 `docs/decisions/FINAL_DECISION_PACKET.md`）。

## 当前案例

- 三个社区平台的公开反馈，共 **360** 条样本（每平台 120）。
- 数据分两层：**样本层**（一条完整反馈）与**证据层**（从原文切出的证据单元）。
- **legacy 与 v2**：早期 legacy 结果保留在 `docs/files/**` 作为中间产物；v2 在 `data/v2/**` 用稳定编号重建。
- 已迁移：695 条唯一命中 legacy 证据迁移到正确样本；B 站 279 条候选已生成 Agent 提案。
- 仍待人工确认：全部 v2 标签未经真人复核；2 条极短歧义证据未定案。

## 它评测什么

- 证据文本能否回到对应原始反馈；
- 标签覆盖与不确定比例；
- 洞察是否有足够证据支撑；
- 产品建议能否回到洞察与证据；
- 运行是否可复现。

指标定义见 `evaluation/metrics.yaml`，阈值见 `evaluation/thresholds.yaml`，方法见 `docs/evaluation/EVALUATION_METHOD.md`。

## 分析与评测流程

反馈 → 证据 → 编码（主题 + 机制）→ 结构化洞察 → 产品假设 → 评测

## 当前结果

只列已能准确陈述的指标（普通语言）：

- 每条反馈都有唯一编号；
- 每条展示证据都能回到对应的原始反馈；
- 覆盖三个平台；
- 证据都带机制标签（约一半为"暂判不准"，诚实标注）；
- 尚无真人复核（当前为机器提案与历史标签）；
- 离线 Demo 同输入同输出。

> 机器给出的标签是**提案**（`agent_proposed`），不是人工复核结论。草稿结构化洞察与产品假设默认不在页面展示。

## 离线 Demo

```bash
python tools/run_demo.py
```

输入几条脱敏反馈，离线生成证据、草稿洞察、待验证产品假设与评测报告。默认不联网、不调用模型。详见 `demo/README.md`。

## 完整抓取链

真实抓取与真实模型调用默认关闭、需显式配置、CI 永不运行。完整流程与安全说明见 `docs/pipeline/FULL_PIPELINE.md`。

## 数据与文件

- 脱敏示例：`demo/examples/sample_feedback.csv`
- 编码手册：`docs/methodology/MECHANISM_CODEBOOK.md`、`SURFACE_TOPIC_CODEBOOK.md`
- 评测方法与结果：`docs/evaluation/`
- 离线 Demo：`demo/`

完整数据下载默认不开放（见 `docs/decisions/FINAL_DECISION_PACKET.md` D-001）。

## 方法与边界

- 人工复核覆盖：当前为 0（`data/v2/human_review_log.csv` 无 `reviewer_type=human`）；
- Agent 提案：B 站标签为机器提案，未经人工确认；
- legacy 历史结果：作为中间产物保留，正用 v2 证据层重新复核；
- 发布状态：`PENDING_USER_DECISIONS`。

## 仓库结构

```
data/v2/            v2 数据底座、迁移、提案、provisional 证据、评测报告
evaluation/         指标 / 阈值 / 失败类型定义
tools/              审计、生成、评测、Demo、页面数据脚本
demo/               离线可运行 Demo
docs/methodology/   编码手册与证据切分指南
docs/review/        复核指南与状态定义、歧义决策包
docs/evaluation/    评测方法与结果草稿
docs/pipeline/      完整抓取链与安全说明
docs/phase1/        迁移与阶段报告
docs/audit/         审计报告
docs/decisions/     延期决策与最终决策包
docs/index.html     展示页
```

## CI 与复现

`.github/workflows/ci.yml` 在 Ubuntu 与 Windows 上运行：编译、静态检查、pytest、v2 审计、Demo smoke、页面静态校验、历史文件保护。分层状态：`legacy_status=BLOCKED`、`v2_migration_status=PASS`、`publication_readiness` 受延期决策约束。

## 许可

Copyright © 2026 Sherlock0717. All rights reserved. 详见 `RIGHTS_AND_USAGE.md`。
