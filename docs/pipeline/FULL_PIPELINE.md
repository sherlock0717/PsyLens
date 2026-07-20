# 完整抓取与分析链（FULL_PIPELINE）

> 说明 PsyLens 从公开反馈到页面数据的完整流程。真实抓取与真实模型调用**默认关闭**，需用户显式配置，**CI 永不运行**。脱敏 Demo（`tools/run_demo.py`）提供离线可运行替代。

## 流程总览

```
候选发现 → 页面抓取 → 评论抓取 → 缓存 → 预清洗 → AI 精修 → 平衡采样
→ 证据抽取 → 主题编码 → 机制编码 → 洞察生成 → 建议生成 → 数据审计 → 页面数据构建
```

## 逐步说明

| 步骤 | 对应脚本 | 输入 | 输出 | 网络/登录 | 说明 |
| --- | --- | --- | --- | --- | --- |
| 候选发现 | `pipeline/discovery/candidate_discovery_template.py`（模板，默认 dry-run 离线） | 平台关键词 | 候选帖子清单 | dry-run 离线；真实检索需网络 | 公开模板（`reconstructed_template`） |
| 页面/评论抓取 | `scripts_public/crawl_tieba_selected.py`、`crawl_bili_selected_auto.py` | 候选清单 | 原始抓取缓存 | 需网络，可能需登录态 | **默认关闭**；不得提交 Cookie/登录缓存 |
| 缓存 | （抓取脚本内）| 抓取结果 | 本地缓存文件 | — | 缓存不入库 |
| 预清洗 | `scripts_public/preclean_feedback_registry.py` | 原始缓存 | 预清洗登记 | 离线 | 去噪、字段规整 |
| 合并 | `scripts_public/merge_phase2_inputs.py` | 多平台预清洗 | 合并输入 | 离线 | 多平台合并 |
| AI 精修 | `scripts_public/ai_curate_feedback.py` | 合并输入 | 精修反馈 | 需模型 API | **默认关闭**；真实模型调用 |
| 平衡采样 | （精修/合并阶段）| 精修反馈 | 平台平衡样本（各 120）| 离线 | 得到 360 条 clean 样本 |
| 证据抽取 → 主题/机制编码 | `scripts_public/run_pipeline.py`（及 AI 精修）| clean 样本 | 证据表 + 标签 | 需模型 API | legacy 阶段产物 |
| 洞察/建议生成 | `run_pipeline.py` | 证据表 | 洞察/建议 | 需模型 API | legacy 中间产物 |
| 数据审计 | `tools/audit_public_data.py` | clean + 证据 + 洞察 | 审计结果 | 离线 | 本仓库新增，确定性 |
| 页面数据构建 | `tools/build_showcase_data.py` | v2 数据 + 评测 | `docs/assets/data/showcase.json` | 离线 | 页面数据驱动 |

## 与当前 v2 的关系

- legacy 阶段（抓取→AI 精修→证据→洞察→建议）产出的历史结果保留在 `docs/files/**`，作为 legacy 中间产物；
- v2 重建（稳定 ID、迁移、离线规则基线提案、provisional 证据、评测、草稿洞察/建议）在 `data/v2/**`；
- 离线 Demo 用脱敏输入复现「拆分→编码→洞察→建议→评测」链路，不含真实抓取与模型。

## 已公开内容

当前仓库公开了主要脚本、配置模板、Prompt 模板、依赖清单、示例输入和离线 Demo：

- 主要脚本：`scripts_public/**`（抓取/精修/预清洗/合并）；
- 候选发现模板：`pipeline/discovery/candidate_discovery_template.py`（默认 dry-run、离线）；
- 配置模板：`pipeline/config/case.example.yaml`、`platforms.example.yaml`（无密钥）；
- Prompt 模板：`pipeline/prompts/*.md`（6 个）；
- legacy 依赖：`pipeline/requirements-legacy.txt`（pandas/openai/requests/bs4 等）；
- 示例输入：`pipeline/examples/**`（脱敏、非真实链接）；
- 离线 Demo：`tools/run_demo.py`（仅标准库，不联网、不调用模型）。

> 部分历史候选发现逻辑与历史 Prompt 无法精确恢复，`pipeline/**` 中相关内容根据现有脚本重建（标记 `reconstructed_template`），不能保证与最初运行逐字一致。

详见 `pipeline/README.md`、`CONFIGURATION.md`、`PROMPT_REFERENCE.md`、`CRAWLING_GUIDE.md`、`SECURITY_AND_PRIVACY.md`、`FAILURE_RECOVERY.md`。
