# 采集与分析流程（pipeline）

本目录公开 PsyLens 从公开反馈到分析数据的**主要脚本、配置模板、Prompt 模板、依赖清单和最小示例**。

> 重要：真实抓取与真实模型调用**默认关闭**、需用户显式配置、**CI 永不运行**。
> 离线 Demo（`tools/run_demo.py`，仅标准库）提供无需联网、无需密钥的可运行替代。
> 部分历史配置与 Prompt 根据现有脚本重建（标记 `reconstructed_template`），不保证与最初运行逐字一致。

## 目录

```
pipeline/
  discovery/candidate_discovery_template.py   候选发现模板（默认 dry-run、离线）
  config/case.example.yaml                    案例配置示例（无密钥）
  config/platforms.example.yaml               平台配置示例（无密钥）
  prompts/                                     6 个 Prompt 模板（reconstructed_template）
  examples/candidate_posts.example.csv         示例候选清单（非真实链接）
  examples/raw_feedback.example.jsonl          示例原始反馈（脱敏）
  requirements-legacy.txt                      legacy 脚本第三方依赖
```

## 完整流程

```
候选发现 → 页面/评论抓取 → 缓存 → 预清洗 → 合并 → AI 精修 → 平衡采样
→ 证据抽取 → 主题编码 → 机制编码 → 洞察生成 → 建议生成 → 数据审计 → 页面数据构建
```

对应脚本、输入输出、网络/登录要求见 `docs/pipeline/FULL_PIPELINE.md` 与同目录其他文档。

## 安全与隐私

- 不得提交 Cookie、Token、API Key、登录态缓存、真实账号、浏览器 profile、未审查缓存；
- 密钥仅通过环境变量提供（见根目录 `.env.example`）；
- 示例数据均脱敏、无真实链接；
- 真实抓取须遵守各平台条款，用户自行承担合规责任。

## 快速开始（离线）

```bash
# 候选发现模板（dry-run，不联网）
python pipeline/discovery/candidate_discovery_template.py --output artifacts/pipeline/candidates.csv

# 端到端离线 Demo（mock，不联网、不调用模型）
python tools/run_demo.py --provider mock --output artifacts/demo/run
```
