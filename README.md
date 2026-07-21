# PsyLens

PsyLens 把分散的玩家反馈整理成可核查的产品线索，并对整条分析链路做可靠性评测。当前案例围绕《英雄联盟》海克斯大乱斗的社区讨论。

- **在线页面**：https://sherlock0717.github.io/PsyLens/
- **完整项目说明**：[`docs/files/PsyLens_project_brief.docx`](docs/files/PsyLens_project_brief.docx)
- **公开数据**：[`data/public/`](data/public/)
- **离线 Demo**：[`demo/`](demo/)

## 当前案例与主要结果

案例整合 NGA、贴吧、B 站三个平台的公开讨论。每个平台等额保留 120 条样本，共 360 条。样本再切分为 927 条证据单元，平均每条样本约 2.58 条证据，全部能在对应公开样本中逐字定位。

**证据单元**：从一条完整反馈中切出的、可以单独判断问题类型的短片段。

主要分布以 441 条可明确分类的证据为分母：

- 具体话题最集中在平衡与数值：270 条，占 61.2%；其次是匹配与对局分配：82 条，占 18.6%。
- 体验机制最集中在胜任受挫：308 条，占 69.8%；其次是公平受损：88 条，占 20.0%。
- 数量较高的交叉组合是平衡与数值 × 胜任受挫，共 138 条。

**体验机制**：玩家在表达中呈现的主要体验方向，例如觉得难以发挥、觉得规则不公平，或觉得官方说明不清楚。

完整分布由 [`tools/summarize_public_analysis.py`](tools/summarize_public_analysis.py) 从公开数据计算，页面读取 [`docs/assets/data/analysis_summary.json`](docs/assets/data/analysis_summary.json) 展示。

## 分析方法

项目采用双层编码。表层话题记录反馈在谈什么，体验机制记录文本呈现的心理体验方向。两层分开记录，使产品问题、心理机制和证据来源可以分别核对。

编码顺序是先判断证据是否能独立成立，再分别标注话题与机制。当文本过短、依赖上下文或同时指向多个方向时，标签保留为 uncertain，避免牵强归类。

## 心理学思路

机制层参考胜任需要、公平判断、组织信任、社群归属与规范安全五个方向的研究，并把这些方向转化为可观察的文本判据。体验类型、操作性定义和参考文献见 [`docs/methodology/PSYCHOLOGY_FRAMEWORK.md`](docs/methodology/PSYCHOLOGY_FRAMEWORK.md)。

交叉组合用于提出可验证的产品问题，再由问卷、访谈、行为日志或实验继续检验。

## 数据处理

处理流程从候选讨论登记开始，依次经过采集、规则预清洗、内容筛选、平台等额抽样、公开脱敏、证据切分与双层编码，最后做完整性与分布审计。

关键操作包括删除回复头与引用残留、移除低信息文本、删除来源链接和账号定位字段、按标点切分证据，并检查每条证据能否在父样本中逐字定位。字段、清洗规则和复现命令见 [`docs/methodology/DATA_CLEANING_AND_CODING.md`](docs/methodology/DATA_CLEANING_AND_CODING.md)。

日期字段覆盖 120 / 360 条样本。当前版本聚焦当前样本的整体分布，时间维度在日期覆盖扩展后启用。

## 可靠性评测

评测把"结果看起来合理"拆成可检查的条件，分为五组：结构完整性、清洗与隐私、编码可用性、分析支撑、运行复现。当前结构完整性全部通过，公开数据 URL 命中为 0，重复文本组为 0。完整方法见 [`docs/evaluation/EVALUATION_METHOD.md`](docs/evaluation/EVALUATION_METHOD.md)。

编码可用性的校准重点是暂时保留为不确定的证据：486 条证据的体验机制标注为 uncertain，主要涉及短文本、上下文依赖和多种解释并存。这批样本是下一步标签边界校准的重点材料。

## 自动校准工具

仓库提供分层抽样、三路独立复检、共识统计和争议分析工具。抽样从公开证据中取 300 条主样本和 30 条重测样本。三个互不查看彼此结果的代理各自独立复检，输出共识标签、争议标签和重复运行稳定性。

本地固定示例用于验证数据流、输出格式和统计流程。OpenAI-compatible 接口作为扩展入口保留，当前公开版本不包含真实模型运行结果。

**自动校准参考集**：由多个互不查看彼此结果的代理独立判断后形成的参考标签，用于发现稳定结果和争议案例。它定位为自动校准参考，人工金标准另行建立。流程见 [`docs/evaluation/AGENT_CALIBRATION_WORKFLOW.md`](docs/evaluation/AGENT_CALIBRATION_WORKFLOW.md)。

## 运行与复现

离线 Demo 默认使用本地固定示例模式，不联网，也不调用外部模型：

```bash
python tools/run_demo.py
```

生成公开分析汇总：

```bash
python tools/summarize_public_analysis.py \
  --public-dir data/public \
  --output artifacts/public_analysis_summary.json
```

检查公开文案表达：

```bash
python tools/lint_public_copy.py --root . --format markdown
```

## 结果使用说明

三个平台采用等额抽样，编码来源包含历史 AI 结果与离线规则提案。证据数量也会受文本长度和切分粒度影响。当前分布用于方法审计、探索性分析和研究设计。它为访谈、问卷、行为分析和实验提供问题线索。总体占比与因果结论由这些后续研究继续检验。

公开数据还包含两个含义不同的字段，各统计一次即可：`mechanism_label=uncertain` 有 486 条，表示机制暂时无法明确归类；`analysis_inclusion_status=included_flagged_uncertain` 有 163 条，表示证据仍被保留但纳入时需要提醒。

## 权利与使用

Copyright © 2026 Sherlock0717. All rights reserved.

代码、数据与文档未采用开放许可证。引用公开页面或项目说明时请注明来源；复制、再分发或用于其他项目需获得授权。详见 [`RIGHTS_AND_USAGE.md`](RIGHTS_AND_USAGE.md)。
