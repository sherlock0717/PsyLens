# PsyLens Reproducibility Boundary（复现边界）

> 本文件说明当前公开仓库能做什么、不能做什么，帮助读者建立合理预期。
> 核心原则：**诚实说明边界，不声称一键完整复现。**

---

## 1. What this repository supports（公开仓库支持什么）

- 阅读项目结构与文档（README、PROJECT_BRIEF、METHODOLOGY、DATA_DICTIONARY）。
- 查看公开结果文件（整洁样本、证据表、验证洞察、行动建议矩阵）。
- 理解处理流程（Public Feedback → Clean Input → Evidence Unit → Mechanism Label → Validated Insight → Action Matrix）。
- 参考公开脚本的接口与实现思路（`scripts_public/`）。

---

## 2. What this repository does not fully support（公开仓库不完全支持什么）

- **不保证完整一键复现**最终结果。
- 缺少完整的 `prompts/`（AI 精修与 pipeline 所需的系统提示文件）。
- 缺少 `config/`（如 `run_pipeline.py` 引用的 case 配置 `case_*.yaml`）。
- 缺少完整的原始抓取数据（仅公开经清洗、平衡后的结果样本）。
- 不包含 `.env`、cookie、调试 HTML、高风险原始抓取数据。

> 因此，直接运行 `scripts_public/run_pipeline.py` 等脚本，会因缺少 prompts、config、原始数据或环境变量而无法端到端跑通。

---

## 3. Public scripts boundary（公开脚本边界）

`scripts_public/` 是**公开版关键脚本**，目的是让读者**理解流程和接口**：

- `crawl_tieba_selected.py` / `crawl_bili_selected_auto.py`：采集示意（依赖 cookie 与平台可用性）。
- `preclean_feedback_registry.py`：预清洗。
- `ai_curate_feedback.py`：AI 辅助精修（依赖模型环境变量）。
- `merge_phase2_inputs.py`：多平台合并与字段标准化。
- `run_pipeline.py`：证据拆分、洞察验证与行动建议生成（依赖 prompts/config）。

它**不等于完整执行包**，也**不承诺**只下载公开仓库即可复现完整结果。

---

## 4. Environment variables（环境变量，仅列变量名）

以下变量仅用于说明脚本运行时会读取的配置项，**不提供任何真实值**，请使用者自行准备：

- `DEEPSEEK_API_KEY`
- `DEEPSEEK_BASE_URL`
- `DEEPSEEK_MODEL`
- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`
- `OPENAI_REVIEW_MODEL`
- （贴吧采集相关）`TIEBA_COOKIE`

> **严禁**将真实密钥、cookie、token 写入仓库任何文件。

---

## 5. How to safely inspect scripts（如何安全查看脚本）

- 建议先运行 `-h` 查看参数，例如：
  ```
  python scripts_public/run_pipeline.py -h
  ```
- **不建议**直接运行抓取脚本（`crawl_*`）；采集涉及平台规则、频率与 cookie，需使用者自行评估与准备。
- 任何 API / cookie 相关配置需使用者自行准备，且不应提交到仓库。

---

## 6. Data ethics / privacy boundary（数据伦理与隐私边界）

- 公开仓库**不包含** `.env`、cookie、调试 HTML、高风险原始抓取数据。
- 使用公开社区反馈时，应遵守各平台规则与隐私边界。
- 展示与引用时，避免暴露个人身份信息与非公开内容。

---

## 7. Future reproducibility improvements（未来可补强的方向）

以下为**未来可能**补强复现性的方向（本阶段不实际新增这些文件）：

- `requirements.txt`（依赖清单）
- `.env.example`（环境变量模板，仅占位）
- `scripts_public/README.md`（脚本说明）
- `prompts_public/`（可公开的提示示例）
- sample input（小规模示例输入）

> 是否新增以上内容，将在后续阶段（如 Phase 4）根据需要与用户确认后再决定。
