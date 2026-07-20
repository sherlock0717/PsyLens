# 采集与分析流程

本目录提供 PsyLens 从候选讨论到分析数据的公开方法、配置与 Prompt 模板。当前公开仓库将流程分为两类：

- **可直接运行的离线流程**：公开数据规范化、统计汇总、离线 Demo 和质量测试；
- **需自行配置的采集流程**：候选发现、页面访问、缓存和模型调用。平台接口与页面结构变化频繁，因此仓库提供输入输出契约和配置模板，不在 CI 中访问真实平台。

## 当前目录

```text
pipeline/
  discovery/candidate_discovery_template.py   候选发现 dry-run 模板
  config/case.example.yaml                    案例配置示例
  config/platforms.example.yaml               平台配置示例
  prompts/                                    证据、编码、洞察与建议 Prompt
  examples/candidate_posts.example.csv        候选帖子示例
  examples/raw_feedback.example.jsonl         脱敏原始反馈示例
  requirements-legacy.txt                     历史采集环境依赖参考
```

## 完整流程

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
→ 页面与项目说明
```

各阶段的输入输出、失败恢复与安全要求见：

- [`docs/pipeline/FULL_PIPELINE.md`](../docs/pipeline/FULL_PIPELINE.md)
- [`docs/pipeline/CONFIGURATION.md`](../docs/pipeline/CONFIGURATION.md)
- [`docs/pipeline/CRAWLING_GUIDE.md`](../docs/pipeline/CRAWLING_GUIDE.md)
- [`docs/pipeline/FAILURE_RECOVERY.md`](../docs/pipeline/FAILURE_RECOVERY.md)
- [`docs/pipeline/SECURITY_AND_PRIVACY.md`](../docs/pipeline/SECURITY_AND_PRIVACY.md)

## 可运行入口

```bash
# 候选发现 dry-run，不访问网络
python pipeline/discovery/candidate_discovery_template.py \
  --output artifacts/pipeline/candidates.csv

# 规范化公开数据
python tools/normalize_public_dataset.py \
  --source-dir data/public \
  --output-dir artifacts/normalized_public

# 生成数据分析汇总
python tools/summarize_public_analysis.py \
  --public-dir data/public \
  --output artifacts/public_analysis_summary.json

# 运行离线端到端示例
python tools/run_demo.py --provider mock --output artifacts/demo/run
```

## 采集实现状态

最初项目使用过平台页面脚本与模型清洗脚本。相关实现依赖当时的平台结构、接口和本地配置，当前公开发布版没有把这些历史脚本作为可维护入口。仓库保留采集契约、字段定义、配置示例和 Prompt，使采集层能够在合规环境中重新实现，同时避免把已失效的页面选择器或接口参数包装成稳定能力。

## 安全要求

- Cookie、Token、API Key、浏览器 profile 和原始缓存不得提交；
- 密钥只通过环境变量注入；
- 真实采集需要遵守平台条款、访问频率限制和适用法律；
- 公开数据经过字段最小化，不包含来源链接与账号定位信息；
- CI 只运行离线脚本和脱敏示例。
