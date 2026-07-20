# PsyLens

社区反馈分析与可靠性评测：把公开社区反馈整理成可回溯证据，并评估从编码到产品假设的每一步是否可靠。

- 展示页：`docs/index.html`（GitHub Pages）
- 当前状态：完成了证据链迁移、离线规则基线和可复现 Demo；标签尚未经过真人复核，结构化洞察与产品假设仍为草稿。

## 当前案例

- 三个社区平台的公开反馈，共 **360** 条样本（每平台 120）。
- 数据分两层：**样本层**（一条完整反馈）与**证据层**（从原文切出的证据单元），证据数量不等于样本数量。
- **legacy 与 v2**：早期 legacy 结果作为中间产物保留；v2 在 `data/v2/**` 用稳定编号重建。
- 已迁移 695 条唯一命中 legacy 证据；B 站 279 条候选由离线规则基线生成初步提案。

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

- 数据迁移结构完整、编号唯一；
- 每条展示证据都能回到对应的原始反馈；
- B 站标签为**离线规则基线**提案，不是人工或模型语义复核；
- 人工复核覆盖当前为 **0**；
- 离线 Demo 同输入同输出，可复现。

## 离线 Demo

```bash
python tools/run_demo.py
```

输入几条脱敏反馈，离线生成证据、草稿洞察、待验证产品假设与评测报告。默认不联网、不调用模型。详见 `demo/README.md`。

## 采集与分析流程

主要脚本、配置模板、Prompt 模板、依赖清单与示例见 `pipeline/README.md` 与 `docs/pipeline/FULL_PIPELINE.md`。真实抓取与真实模型调用默认关闭、需显式配置、CI 永不运行。

## 数据与文件

- 公开分析数据（脱敏、无来源链接）：`data/public/`
- 脱敏示例：`demo/examples/sample_feedback.csv`
- 编码手册：`docs/methodology/MECHANISM_CODEBOOK.md`、`SURFACE_TOPIC_CODEBOOK.md`
- 评测方法与结果：`docs/evaluation/`
- 离线 Demo：`demo/`
- 正式项目说明：`docs/files/PsyLens_project_brief.docx`

仓库提供脱敏示例与公开分析数据；来源链接和内部迁移文件不作为展示页入口。

## 方法范围

- 离线规则基线不是人工复核，也不是模型语义判断；
- 草稿洞察和产品假设尚未成为正式结论；
- 原始来源链接不在展示页和公开数据副本中提供；
- 产品假设仍需实验验证。

## 仓库结构

```
data/v2/            v2 数据底座、迁移、规则基线提案、provisional 证据、评测报告
data/public/        公开脱敏数据副本（无来源链接）
evaluation/         指标 / 阈值 / 失败类型定义
tools/              审计、生成、评测、Demo、页面数据、公开数据、DOCX 脚本
demo/               离线可运行 Demo
pipeline/           采集与分析流程脚本、配置模板、Prompt 模板、示例
docs/methodology/   编码手册与证据切分指南
docs/review/        复核指南与状态定义、歧义决策包
docs/evaluation/    评测方法与结果草稿
docs/pipeline/      完整采集与分析流程说明
docs/decisions/     延期决策与最终决策包
docs/index.html     展示页
```

## CI 与复现

`.github/workflows/ci.yml` 在 Ubuntu 与 Windows 上运行：编译、Ruff 静态检查、pytest、v2 审计、评测器、公开数据构建、页面数据构建、Demo smoke、页面静态校验、DOCX 存在与可读、历史文件保护。

## 许可

Copyright © 2026 Sherlock0717. All rights reserved. 详见 `RIGHTS_AND_USAGE.md`。
