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
| 候选发现 | （人工/脚本挑选帖子）| 平台关键词 | 候选帖子清单 | 需网络 | 当前候选发现脚本未纳入公开仓库（见缺失项） |
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
- v2 重建（稳定 ID、迁移、Agent 提案、provisional 证据、评测、草稿洞察/建议）在 `data/v2/**`；
- 离线 Demo 用脱敏输入复现「拆分→编码→洞察→建议→评测」链路，不含真实抓取与模型。

## 缺失项（当前公开仓库不含）

- 候选发现脚本；
- `prompts/` 与 `config/case_*.yaml`（真实运行配置）；
- 真实示例抓取输入；
- mock provider（legacy 脚本无 dry-run/mock，Demo 已补）；
- `requirements.txt` 针对 legacy 脚本的第三方依赖（pandas/openai/requests/bs4 等）。

详见 `CONFIGURATION.md`、`PROMPT_REFERENCE.md`、`CRAWLING_GUIDE.md`、`SECURITY_AND_PRIVACY.md`、`FAILURE_RECOVERY.md`。
