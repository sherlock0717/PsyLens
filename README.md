# PsyLens

PsyLens 是一个将多平台公开游戏社区反馈转化为可追溯证据链、心理机制解释与产品行动建议的分析工作流（analysis workflow）。当前公开案例以《英雄联盟》海克斯大乱斗模式为对象，整合 NGA、贴吧、B 站三个平台的公开反馈，展示从非结构化玩家表达到结构化洞察资产的完整过程。

> 说明：本项目是个人研究与作品集性质的公开案例，用于展示方法与工作流，**不是任何企业的内部项目，也不代表 Riot Games 或任何公司的内部判断**。

GitHub Pages 展示页：`https://sherlock0717.github.io/PsyLens/`

---

## 1. Project Overview（项目概述）

- **PsyLens 是什么**：一套把「公开社区反馈 → 证据链 → 心理机制 → 行动建议」串起来的分析工作流，强调结论可追溯、边界可说明。
- **当前案例**：《英雄联盟》海克斯大乱斗（Hex ARAM）模式的社区讨论。
- **使用的数据**：NGA、贴吧、B 站三平台的**公开**社区反馈（评论、回复、热评等）。
- **输出的结果**：三平台整洁样本、证据单元表（evidence unit）、验证洞察（validated insights）、行动建议矩阵（action matrix），以及一个可对外阅读的展示页。
- **适合谁阅读**：用户研究（UXR）、游戏产品 / 模式策划、社区运营与发行、以及关注「AI 辅助分析工作流」的读者。

---

## 2. Case Scope（案例范围）

| 维度 | 内容 |
| --- | --- |
| 案例对象 | 《英雄联盟》海克斯大乱斗模式 |
| 数据来源 | NGA、贴吧、B 站公开反馈 |
| 样本规模 | 360 条整洁样本，三平台各 120 条 |
| 证据单元 | 697 个 evidence unit |
| 验证洞察 | 19 条 validated insights |
| 行动建议 | `docs/files/05_action_matrix.json`（AI 生成/辅助生成的行动建议矩阵） |

> 上述数字与仓库现有公开文件一致；如需逐行核验，请以 `docs/files/` 下实际文件为准。

---

## 3. Core Questions（核心问题）

（整理自 `docs/index.md` 的既有研究问题，未新增未经支持的问题）

1. 玩家围绕海克斯大乱斗，主要在争议什么？（重点观察玩法/机制、队友互动、英雄体验、规则归因）
2. 这些高频表达更稳定地指向哪类体验机制？（重点比较胜任受挫、公平威胁及其他补充机制）
3. 不同平台语境下，主机制是否一致？（比较 NGA、贴吧、B 站的表达风格差异与结论一致性）
4. 这些反馈如何转化为产品、社区与研究可用的行动建议？

---

## 4. Method Framework（方法框架）

```
Public Feedback → Clean Input → Evidence Unit → Mechanism Label → Validated Insight → Action Matrix
公开反馈        → 整洁输入    → 证据单元      → 机制标签        → 验证洞察          → 行动建议矩阵
```

| 步骤 | 输入 | 处理 | 产出 | 对应文件 |
| --- | --- | --- | --- | --- |
| Public Feedback → Clean Input | 三平台公开反馈 | 预清洗、AI 辅助精修、按平台平衡合并、字段标准化 | 整洁样本 | `docs/files/input_feedback_phase2_multiplatform_clean.csv` |
| Clean Input → Evidence Unit | 整洁样本 | 将一条反馈拆成可独立判断的证据单元 | 证据单元表 | `docs/files/final_evidence_table.csv` |
| Evidence Unit → Mechanism Label | 证据单元 | 标注 surface_topic 与心理机制标签、置信度 | 带机制标签的证据表 | `docs/files/final_evidence_table.csv` |
| Mechanism Label → Validated Insight | 带标签证据 | 按共现频率/强度收束成洞察，并标注是否需人工复核 | 验证洞察 | `docs/files/04_validated_insights.jsonl` |
| Validated Insight → Action Matrix | 验证洞察 | 生成分层行动建议（AI 辅助） | 行动建议矩阵 | `docs/files/05_action_matrix.json` |

方法细节见 [`METHODOLOGY.md`](METHODOLOGY.md)。

---

## 5. Key Public Outputs（关键公开产物）

- [`docs/files/input_feedback_phase2_multiplatform_clean.csv`](docs/files/input_feedback_phase2_multiplatform_clean.csv)：三平台整洁样本（360 条，三平台各 120）。
- [`docs/files/final_evidence_table.csv`](docs/files/final_evidence_table.csv)：证据单元表（697 个 evidence unit），含 surface_topic、mechanism_label、confidence 等字段。
- [`docs/files/04_validated_insights.jsonl`](docs/files/04_validated_insights.jsonl)：19 条验证洞察，含 supporting_ids 与 needs_human_review 标记。
- [`docs/files/05_action_matrix.json`](docs/files/05_action_matrix.json)：行动建议矩阵，含 safe / balanced / bold 三层建议（AI 生成/辅助生成，需配合人工判断）。
- `docs/files/PsyLens_enterprise_project_brief_v3.docx`：项目说明文档（当前展示页下载入口指向此版本）。
- `docs/files/PsyLens_enterprise_project_brief_v4.docx`：项目说明文档的另一版本。**仓库中同时保留 v3 与 v4 文件，后续需确认展示页应指向哪一版**；本仓库不擅自删除或改名任何一版。

字段级说明见 [`DATA_DICTIONARY.md`](DATA_DICTIONARY.md)。

---

## 6. Repository Structure（仓库结构）

```
PsyLens/
├── README.md                 # 项目入口（本文件）
├── PROJECT_BRIEF.md          # Markdown 版项目说明
├── METHODOLOGY.md            # 方法论：处理链路、标签体系、证据链、AI 边界
├── DATA_DICTIONARY.md        # 数据字典：公开结果文件的字段说明
├── REPRODUCIBILITY.md        # 复现边界：公开仓库能做什么、不能做什么
├── 公开版文件清单.txt         # 公开/不公开文件清单
├── scripts_public/           # 公开版关键脚本（用于理解流程与接口）
└── docs/                     # GitHub Pages 根目录
    ├── index.html            # 展示页
    ├── index.md              # 展示页的 Markdown 版内容
    ├── style.css             # 页面样式
    ├── assets/               # 页面图表与展示素材（PNG / SVG）
    └── files/                # 公开结果文件（CSV / JSONL / JSON / DOCX）
```

---

## 7. How to Read This Repository（建议阅读顺序）

1. 先看 GitHub Pages 展示页，建立整体印象。
2. 再看 [`PROJECT_BRIEF.md`](PROJECT_BRIEF.md)，理解背景、范围与结论。
3. 再看 [`METHODOLOGY.md`](METHODOLOGY.md)，理解方法链路与判断边界。
4. 再看 [`DATA_DICTIONARY.md`](DATA_DICTIONARY.md)，理解字段含义。
5. 再看 `docs/files/` 下公开结果文件，核对数据与洞察。
6. 最后看 `scripts_public/`，理解处理流程与接口实现。

---

## 8. Reproducibility Boundary（复现边界）

- 当前公开仓库适合：**阅读项目、审查项目结构、理解方法、查看公开结果**。
- 公开仓库**不等于**完整本地执行包。
- 公开仓库当前**缺少**完整重跑所需的：prompts、config、完整原始抓取数据、私有环境变量。
- `scripts_public/` 主要用于**理解流程和接口**，**不承诺一键复现完整结果**。
- 详细说明见 [`REPRODUCIBILITY.md`](REPRODUCIBILITY.md)。

---

## 9. AI Assistance and Human Review Boundary（AI 辅助与人工复核边界）

- 部分清洗、分类、洞察收束和行动建议**包含 AI 辅助**。
- AI 产物**不应被理解为完全人工的研究结论**。
- 页面与文档中的结论，需要与证据表（`final_evidence_table.csv`）、验证洞察（`04_validated_insights.jsonl`）以及人工复核边界**一起阅读**。
- `docs/files/05_action_matrix.json` 是 **AI 生成/辅助生成**的行动建议矩阵，使用时需配合人工判断。
- 部分洞察在 `04_validated_insights.jsonl` 中带有 `needs_human_review: true` 标记，表示证据有限、需人工复核。

---

## 10. Limitations（局限性）

- 数据来自**公开社区**，不代表所有玩家。
- 三平台各 120 条是公开案例中的**平衡样本**，不等于自然舆情分布。
- 心理机制标签是**解释性框架**，不是临床测量。
- AI 辅助分类**存在误差**，需人工复核。
- 行动建议是基于公开反馈形成的**产品假设**，**不代表 Riot 或任何企业的内部判断**。

---

## 11. Public Page（公开页面）

GitHub Pages: `https://sherlock0717.github.io/PsyLens/`

---

## 12. License / Usage Note（许可与使用说明）

当前仓库用于作品集展示、公开结果说明与方法结构参考。使用或引用时请保留项目来源说明。

本仓库当前**没有正式的开源 License 文件**；如后续补充，将以仓库根目录的 `LICENSE` 为准。
