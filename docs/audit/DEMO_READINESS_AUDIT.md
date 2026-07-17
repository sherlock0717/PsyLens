# 完整抓取链与小规模 Demo 准备度审计（DEMO_READINESS_AUDIT）

> 审查 `scripts_public/**`。本阶段只审计与设计，不实现 Demo、不运行抓取、不调用模型。

## 1. 完整流程链与每步状态

| 步骤 | 脚本 | 输入 | 输出 | 依赖 | 网络 | 可运行性 | 缺失 / 风险 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 候选发现 | **（缺失）** | — | `*_selected.csv` | — | — | 不可 | 公开仓库无候选发现 / 选种脚本 |
| 页面/评论抓取（贴吧） | `crawl_tieba_selected.py` | `*_selected.csv`（缺） | registry CSV | requests, bs4, pandas | 是 | 不可（缺输入+依赖） | 读 `TIEBA_COOKIE`/`--cookie-file`；写 debug HTML；输出含 `author_name` |
| 页面/评论抓取（B站） | `crawl_bili_selected_auto.py` | `*_selected.csv`（缺） | registry + debug CSV | requests, pandas | 是（B站 API + WBI 签名） | 不可（缺输入+依赖） | 读 `--cookie-file`；debug 行含评论者 `uname` |
| 预清洗 | `preclean_feedback_registry.py` | registry CSV | preclean CSV | pandas | 否 | 结构可跑（缺依赖/输入） | 确定性、离线 |
| AI 精修 | `ai_curate_feedback.py` | preclean CSV | curated CSV | openai, pandas | 是（模型 API） | 不可（缺 Key/依赖） | 读 `DEEPSEEK_API_KEY`/`OPENAI_API_KEY`；有 3 次重试 + 降级 fallback |
| 平衡合并 | `merge_phase2_inputs.py` | 多平台 curated CSV | clean CSV | pandas | 否 | 结构可跑 | 按 platform 取每平台 120；`id=range(1,N+1)` 重编号（**与错位问题相关**） |
| 证据抽取+主题+机制+洞察+建议 | `run_pipeline.py` | clean CSV | 01–05 产物 | openai, pandas, pyyaml, dotenv, tqdm | 是（模型 API） | 不可（缺 prompts/config/Key/依赖） | 需 `prompts/01–05*.txt`、`config/case_*.yaml`（均缺） |
| 数据审计 | `tools/audit_public_data.py`（本任务新增） | 公开结果文件 | JSON/CSV 报告 | 标准库 | 否 | **可运行** | 离线、确定性 |
| 页面数据 | `docs/files/**` | — | — | — | — | — | 见数据关联审计 |

## 2. 关键缺失项（相对可复现 / Demo）

- `requirements.txt` / `pyproject.toml`：**均缺失**（脚本依赖 pandas/openai/requests/bs4/pyyaml/dotenv/tqdm 均未声明，当前环境亦未安装）。
- `.env.example`：**缺失**（变量名仅在 `REPRODUCIBILITY.md` 列出）。
- `prompts/`（01–05 系统提示）：**缺失**，`run_pipeline.py` 硬依赖。
- `config/case_*.yaml`：**缺失**，`run_pipeline.py` 需 `--case`。
- 示例输入 sample input：**缺失**。
- mock provider / dry-run：**缺失**（无离线模拟、无 `--dry-run`）。
- `.github/workflows/`：**当前仓库不存在**（记录在案）。
- `tests/`：原仓库无（本任务新增 `tests/test_public_data_audit.py`）。

## 3. 错误处理 / 稳健性

- 重试：`ai_curate_feedback.py`（3 次 + 退避）、`crawl_tieba_selected.py`（fetch 重试）有；其余较少。
- 限速：贴吧/ B 站抓取有 `sleep` + 随机抖动。
- 日志：以 `print` 为主，无结构化日志。
- checkpoint / resume：**无**（长抓取中断需重来）。
- 输出目录：`run_pipeline.py` 写 `data/processed/`；其余写 `--output` 指定路径。**默认不写 `docs/files/`**，即默认不会覆盖公开历史结果。
  - ⚠️ 但若使用者手动将 `--output` 指向 `docs/files/`，仍可能覆盖公开结果 —— Demo 设计需显式禁止。

## 4. 安全风险

- **Cookie**：贴吧脚本从 `TIEBA_COOKIE` 环境变量或 `--cookie-file` 读取；B 站脚本从 `--cookie-file` 读取。仓库内**未发现**硬编码 Cookie/Key（已扫描脚本）。
- **debug HTML**：贴吧脚本 `--debug-html-dir` 会把原始页面（可能含账号/楼层信息）落盘；需确保不提交。
- **个人线索**：抓取中间产物含 `author_name`（贴吧）、`uname`（B 站评论者）；但**公开整洁样本（merge 输出）已丢弃这些列**（final 列不含作者名）。
- **日志泄露 Key**：未发现将 Key 打印到日志的代码；但异常 fallback 会把 `str(e)` 写入产物字段（`error:{e}`），需注意异常信息不含敏感值。
- `.gitignore`：原仓库无（本任务已新增，忽略 `.env`/cookie/artifacts）。

## 5. 小规模 Demo 准备度评估

当前**不具备**开箱即用的离线 Demo（缺依赖声明、prompts、config、sample input、mock、dry-run）。但离线 Demo 的**素材条件已具备**：已有整洁样本、证据表、洞察、行动矩阵可作为确定性回放数据。

### 建议的最小 Demo 设计（本阶段仅设计）

- **默认离线**：不跑 crawler、不调模型；提供 `--offline`（默认开启）。
- **脱敏 sample input**：从整洁样本抽取小样本（如每平台 5–10 条），去除 URL 中的可定位 id。
- **确定性 mock provider**：以规则 / 固定映射替代模型调用，保证同输入同输出。
- **输出隔离**：写入 `artifacts/demo/<run_id>/`，**严禁**写 `docs/files/`；启动时校验输出目录不在 `docs/`。
- **展示内容**：证据拆分 → 主题/机制编码 → 结构化洞察 → 建议关联，并调用 `tools/audit_public_data.py` 产出验证报告。
- **不修改历史结果**：Demo 只读 `docs/files/**`，不写回。
- 需先补 `requirements.txt` + `.env.example` + `prompts_public/`（占位）+ `scripts_public/README.md`。

> 准备度结论：**尚未就绪（Not Ready）**，但改造成本可控；关键前置是依赖声明、mock provider 与输出隔离。
