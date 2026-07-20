# PsyLens

PsyLens 是一套社区反馈分析与可靠性评测工作流。当前案例围绕《英雄联盟》海克斯大乱斗社区讨论展开，将多平台公开反馈整理为样本与证据单元，再从具体话题、体验机制和数据可靠性三个层面分析。

- **在线页面**：https://sherlock0717.github.io/PsyLens/
- **完整项目说明**：[`docs/files/PsyLens_project_brief.docx`](docs/files/PsyLens_project_brief.docx)
- **公开数据**：[`data/public/`](data/public/)
- **离线 Demo**：[`demo/`](demo/)

## 当前案例

| 项目 | 结果 |
| --- | --- |
| 数据来源 | NGA、贴吧、B 站公开讨论 |
| 样本设计 | 三个平台各 120 条，共 360 条 |
| 证据单元 | 927 条，平均每条样本 2.575 条 |
| 文本回溯 | 927 条证据均能在对应公开样本中定位 |
| 结构问题 | 孤立证据 0，平台错配 0，重复文本组 0 |
| 日期覆盖 | 120 条有日期，240 条日期为空 |

## 主要分析结果

### 具体话题

排除 `other_uncertain` 后，共有 441 条证据能够分配具体话题：

- 平衡与数值：270 条，占 61.2%；
- 匹配与对局分配：82 条，占 18.6%；
- 活动与玩法设计：24 条，占 5.4%；
- 成长与养成：20 条，占 4.5%；
- 社区冲突与氛围：18 条，占 4.1%。

### 体验机制

排除 `uncertain` 后，共有 441 条证据能够分配主要体验机制：

- 胜任受挫：308 条，占 69.8%；
- 公平受损：88 条，占 20.0%；
- 信任与沟通落差：24 条，占 5.4%；
- 归属感下降：11 条，占 2.5%；
- 规范与安全风险：10 条，占 2.3%。

### 话题与机制交叉

数量较高的具体组合包括：

- 平衡与数值 × 胜任受挫：138 条；
- 平衡与数值 × 公平受损：35 条；
- 匹配与对局分配 × 胜任受挫：22 条；
- 匹配与对局分配 × 公平受损：16 条；
- 沟通与透明度 × 信任与沟通落差：13 条。

完整分布由 [`tools/summarize_public_analysis.py`](tools/summarize_public_analysis.py) 从公开数据计算，页面读取 [`docs/assets/data/analysis_summary.json`](docs/assets/data/analysis_summary.json) 展示。

## 心理学分析框架

项目采用双层编码：

1. **表层话题**记录反馈正在讨论的问题；
2. **体验机制**记录文本呈现的心理体验方向。

机制层参考胜任需要、公平判断、组织信任、社群归属与规范安全研究，并通过固定纳入、排除和相邻标签区分规则转化为文本编码。详细构念、操作性定义和参考文献见 [`docs/methodology/PSYCHOLOGY_FRAMEWORK.md`](docs/methodology/PSYCHOLOGY_FRAMEWORK.md)。

## 数据处理流程

```text
候选讨论登记
→ 页面与回复采集
→ 原始缓存
→ 规则预清洗
→ 内容筛选与字段规整
→ 平台等额抽样
→ 公开脱敏
→ 证据单元切分
→ 话题与机制编码
→ 完整性与分布审计
```

关键操作包括：删除回复头、引用残留、图片路径和多余空白；移除空文本与低信息噪声；删除来源链接和账号定位字段；按标点切分证据；检查证据文本是否能在父样本中逐字定位；扫描重复、空值、URL 和非法标签。

详细字段、清洗规则和复现命令见 [`docs/methodology/DATA_CLEANING_AND_CODING.md`](docs/methodology/DATA_CLEANING_AND_CODING.md)。

## 可靠性评测

评测分为五组：

- **结构完整性**：ID、父样本、平台和文本定位；
- **清洗与隐私**：字段白名单、URL、重复、空值和文件哈希；
- **编码可用性**：合法标签、不确定比例、标签边界和编码来源；
- **分析支撑**：结论是否带有证据、样本量、分母和平台范围；
- **运行复现**：同输入输出一致、manifest 完整、跨平台 CI。

当前最明显的质量风险是机制不确定率较高：486 / 927，约 52.4%。这项结果提示短文本、上下文依赖和标签边界仍需要更细的编码设计。完整评测方法见 [`docs/evaluation/EVALUATION_METHOD.md`](docs/evaluation/EVALUATION_METHOD.md)。

## 两种不确定性

公开数据包含两个含义不同的字段：

- `mechanism_label=uncertain`：486 条，表示无法明确判断体验机制；
- `analysis_inclusion_status=included_flagged_uncertain`：163 条，表示证据仍被保留，但纳入时存在上下文或解释风险。

两者分别统计，不能合并为同一“不确定率”。

## 离线 Demo

```bash
python tools/run_demo.py
```

Demo 默认使用确定性 mock provider，不联网，也不调用外部模型。输出写入 `artifacts/`，包括 JSON、Markdown、HTML 和 manifest。

生成公开分析汇总：

```bash
python tools/summarize_public_analysis.py \
  --public-dir data/public \
  --output artifacts/public_analysis_summary.json
```

规范化公开数据到独立目录：

```bash
python tools/normalize_public_dataset.py \
  --source-dir data/public \
  --output-dir artifacts/normalized_public
```

## 仓库结构

```text
data/public/                           公开脱敏样本、证据与字段说明
demo/                                  离线分析示例
docs/index.html                        GitHub Pages 展示页
docs/methodology/                      心理框架、编码与清洗方法
docs/evaluation/                       评测方法
evaluation/                            指标与失败类型配置
pipeline/                              采集、配置和 Prompt 模板
tools/                                 公开数据规范化、统计与 Demo 入口
tests/                                 数据、页面与文档校验
```

## 解释边界

三个平台采用等额抽样，编码来源包含历史 AI 结果与离线规则提案，且证据数量会受到文本长度和切分粒度影响。因此当前分布用于方法审计、探索性分析和后续研究设计，不直接代表总体玩家意见占比，也不构成产品效果或心理状态的因果结论。

## 权利与使用

Copyright © 2026 Sherlock0717. All rights reserved.

代码、数据与文档未采用开放许可证。引用公开页面或项目说明时请注明来源；复制、再分发或用于其他项目需获得授权。详见 [`RIGHTS_AND_USAGE.md`](RIGHTS_AND_USAGE.md)。
