# PsyLens

PsyLens 是一套社区反馈分析与可靠性评测工作流。当前案例围绕《英雄联盟》海克斯大乱斗社区讨论展开，从三平台公开反馈中整理样本、拆分证据单元、记录主题与机制编码，并通过离线 Demo 检查数据关联和输出复现性。

- **在线页面**：https://sherlock0717.github.io/PsyLens/
- **项目说明**：[`docs/files/PsyLens_project_brief.docx`](docs/files/PsyLens_project_brief.docx)
- **公开数据**：[`data/public/`](data/public/)
- **离线 Demo**：[`demo/`](demo/)

## 当前案例

| 项目 | 内容 |
| --- | --- |
| 研究对象 | 海克斯大乱斗社区讨论 |
| 数据来源 | NGA、贴吧、B 站公开反馈 |
| 公开样本 | 360 条，每个平台 120 条 |
| 候选证据 | 927 条，其中 163 条标记为暂不确定 |
| 编码状态 | 历史 AI 编码与离线规则基线均保留来源和复核状态 |

公开页面与 `data/public/` 使用脱敏副本，不包含原始来源链接。

## 分析流程

```text
公开反馈
  → 样本整理
  → 证据单元拆分
  → 主题与机制编码
  → 结构化观察
  → 产品假设
  → 可靠性评测
```

项目重点检查以下问题：

- 样本和证据是否具有稳定、唯一的编号；
- 证据文本能否关联到对应样本；
- 标签、不确定项和复核状态是否完整记录；
- 洞察和产品假设能否回到支撑证据；
- 相同输入与配置是否产生一致输出。

指标定义见 [`evaluation/metrics.yaml`](evaluation/metrics.yaml)，方法说明见 [`docs/evaluation/EVALUATION_METHOD.md`](docs/evaluation/EVALUATION_METHOD.md)。

## 公开文件

- [`data/public/samples_public.csv`](data/public/samples_public.csv)：360 条脱敏样本；
- [`data/public/evidence_public.csv`](data/public/evidence_public.csv)：927 条候选证据；
- [`data/public/public_manifest.json`](data/public/public_manifest.json)：字段、数量和文件哈希；
- [`docs/methodology/MECHANISM_CODEBOOK.md`](docs/methodology/MECHANISM_CODEBOOK.md)：机制编码手册；
- [`docs/methodology/SURFACE_TOPIC_CODEBOOK.md`](docs/methodology/SURFACE_TOPIC_CODEBOOK.md)：主题编码手册；
- [`pipeline/README.md`](pipeline/README.md)：采集与分析流程模板；
- [`docs/files/PsyLens_project_brief.docx`](docs/files/PsyLens_project_brief.docx)：正式项目说明。

## 离线 Demo

```bash
python tools/run_demo.py
```

Demo 默认使用确定性 mock provider，不联网，也不调用外部模型。输出写入独立的 `artifacts/` 目录，包括 JSON、Markdown 和 HTML 报告。

详见 [`demo/README.md`](demo/README.md)。

## 仓库结构

```text
data/public/        公开脱敏数据
demo/               离线运行示例
evaluation/         指标与阈值定义
pipeline/           采集、Prompt 和配置模板
docs/               展示页、方法文档与项目说明
tools/run_demo.py   Demo 运行入口
```

## 当前状态

- 公开数据、稳定编号、证据关联和离线 Demo 已完成；
- B 站编码采用离线规则基线，尚未经过真人复核；
- 两条极短证据仍保留为待确认项；
- 结构化观察和产品假设保留草稿状态；
- 产品假设需要结合实验、访谈或上线指标继续验证。

## 权利与使用

Copyright © 2026 Sherlock0717. All rights reserved.

代码、数据与文档未采用开放许可证。引用公开页面或项目说明时请注明来源；复制、再分发或用于其他项目需获得授权。详见 [`RIGHTS_AND_USAGE.md`](RIGHTS_AND_USAGE.md)。
