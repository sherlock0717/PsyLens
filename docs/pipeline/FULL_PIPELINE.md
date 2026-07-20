# 完整采集与分析流程

本文说明 PsyLens 从候选讨论到页面结果的完整方法链。真实平台访问与外部模型调用需要自行配置，不在 GitHub Actions 中执行；公开仓库中的数据规范化、统计、Demo 和质量检查可以离线运行。

## 1. 流程总览

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
→ 结构化分析
→ 可靠性评测
→ 页面与项目说明
```

## 2. 阶段与数据契约

| 阶段 | 主要输入 | 主要操作 | 输出 | 当前公开实现 |
| --- | --- | --- | --- | --- |
| 候选发现 | 关键词、平台与时间窗 | 建立候选讨论登记，记录检索主题和入口 | 候选帖子 CSV | `pipeline/discovery/candidate_discovery_template.py`（dry-run） |
| 页面与回复采集 | 候选登记 | 限速访问、分页、重试、缓存原始响应 | 原始反馈 JSONL / CSV | 方法与配置模板；真实访问需自行实现 |
| 原始缓存 | 页面响应 | 按平台和采集批次保存，不覆盖旧缓存 | 本地缓存目录 | 不进入仓库 |
| 规则预清洗 | 原始反馈 | 删除回复头、图片路径、引用残留和多余空白 | 预清洗文本 | 规则见数据方法文档 |
| 内容筛选 | 预清洗文本 | 排除空文本、标记噪声、离题和低信息表达 | 可用反馈登记 | Prompt 与字段契约公开 |
| 平衡抽样 | 可用反馈 | 按平台与粗主题控制覆盖，确定稳定顺序 | 360 条样本 | 当前公开数据为 3 × 120 |
| 公开脱敏 | 分析样本 | 移除来源与身份字段，屏蔽联系方式和链接 | `data/public/samples_public.csv` | `tools/normalize_public_dataset.py` |
| 证据切分 | 完整样本文本 | 按标点切分、最小长度过滤、父样本定位 | `evidence_public.csv` | 规则见 `EVIDENCE_UNIT_GUIDE.md` |
| 双层编码 | 证据单元 | 分配表层话题、体验机制与不确定类别 | 编码证据表 | codebook、Prompt 与公开结果 |
| 数据审计 | 样本与证据 | ID、父样本、文本定位、重复、空值与分布检查 | 分析汇总 JSON | `tools/summarize_public_analysis.py` |
| 展示与文档 | 分析汇总 | 生成页面、README 和项目说明 | Pages / DOCX | `docs/` 与项目说明生成器 |

## 3. 候选发现

候选发现阶段需要避免只选择高互动或观点极端的帖子。登记表至少包含：

- 平台；
- 候选主题；
- 时间窗；
- 讨论入口；
- 主帖或回复类型；
- 采集优先级；
- 排除理由。

`candidate_discovery_template.py` 默认只生成离线示例，不访问平台。真实检索可以替换为合规的搜索接口或人工候选登记，但输出字段应保持一致。

## 4. 页面访问、限速与缓存

真实采集需要实现：

- 明确 User-Agent；
- 请求间隔与随机抖动；
- 最大重试次数和退避；
- 分页终止条件；
- HTTP 状态和解析失败日志；
- 原始响应缓存；
- 增量续跑与去重。

原始缓存承担复查与失败恢复功能，不能直接作为公开数据。登录态、Cookie、浏览器 profile 和接口签名保存在本地环境，不写入配置示例或日志。

## 5. 清洗、筛选与抽样

规则预清洗只处理可确定的格式噪声，不改变观点。内容筛选关注文本是否具有可解释的体验、归因或诉求。平台等额抽样在当前案例中产生三个平台各 120 条的结构，用于保证平台覆盖。

详细操作见 [`../methodology/DATA_CLEANING_AND_CODING.md`](../methodology/DATA_CLEANING_AND_CODING.md)。

## 6. 证据与编码

一条样本可以产生零到多个证据。每条证据必须保留父样本，文本能够在父样本中定位。表层话题和体验机制分别编码，并保留 `other_uncertain` 与 `uncertain`。

- 证据切分：[`../methodology/EVIDENCE_UNIT_GUIDE.md`](../methodology/EVIDENCE_UNIT_GUIDE.md)
- 表层话题：[`../methodology/SURFACE_TOPIC_CODEBOOK.md`](../methodology/SURFACE_TOPIC_CODEBOOK.md)
- 体验机制：[`../methodology/MECHANISM_CODEBOOK.md`](../methodology/MECHANISM_CODEBOOK.md)
- 心理学框架：[`../methodology/PSYCHOLOGY_FRAMEWORK.md`](../methodology/PSYCHOLOGY_FRAMEWORK.md)

## 7. 公开分析与评测

公开分析由 `tools/summarize_public_analysis.py` 计算，包括：

- 样本与证据数量；
- 每样本证据密度；
- 话题和机制分布；
- 话题 × 机制交叉；
- 平台分布；
- ID、父样本、平台和文本定位；
- 重复、URL 和缺失字段。

评测方法见 [`../evaluation/EVALUATION_METHOD.md`](../evaluation/EVALUATION_METHOD.md)。

## 8. 当前可复现命令

```bash
python tools/normalize_public_dataset.py \
  --source-dir data/public \
  --output-dir artifacts/normalized_public

python tools/summarize_public_analysis.py \
  --public-dir data/public \
  --output artifacts/public_analysis_summary.json

python tools/run_demo.py --provider mock --output artifacts/demo/run

python -m pytest demo/tests tests -q
```

## 9. 当前实现边界

公开仓库提供完整方法链、数据契约、配置模板、Prompt、脱敏数据和离线运行入口。历史平台采集脚本依赖当时的页面结构与接口参数，当前版本没有把这些脚本标记为稳定工具。重新接入真实平台时，应依据本文件的数据契约实现并完成小规模验证，不能直接假定历史接口仍然有效。
