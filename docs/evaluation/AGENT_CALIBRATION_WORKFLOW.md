# 多代理自动校准流程

这份文档说明 PsyLens v1.1 的自动校准流程：用多个互不查看彼此结果的代理，对分层证据做独立复检，输出一致结果、争议标签和重复运行稳定性。

校准结果定位为自动校准参考，用于发现稳定结论和需要重点核对的标签，人工金标准另行建立，也不覆盖公开数据的现有标签。

## 名词解释

- **证据单元**：从一条完整反馈中切出的、可以单独判断问题类型的短片段。
- **自动校准参考集**：由多个互不查看彼此结果的代理独立判断后形成的参考标签。
- **一致程度**：三名代理给出相同标签的比例，用来看哪些判断稳定。
- **争议项**：三路不同或边界判断冲突的证据，进入争议队列等待裁决。

## 流程步骤

| 步骤 | 命令 | 产出 |
| --- | --- | --- |
| 抽样 | `python tools/calibration/build_calibration_sample.py --config config/calibration/calibration.yaml` | 公开分层样本、私有映射、抽样报告 |
| 复检 | `python tools/calibration/run_agent_reviews.py --provider mock --input data/calibration/calibration_sample.csv` | 三路代理复检结果（默认写入 `artifacts/calibration/mock_self_test/reviews`） |
| 共识 | `python tools/calibration/build_agent_consensus.py --input-dir <reviews> --output-dir <consensus>` | 共识、争议队列、统计报告 |
| 争议 | `python tools/calibration/analyze_disagreements.py --input <consensus>/consensus_reference.csv --output <report>` | 争议明细与 Codebook 改进提案 |

## 分层抽样

抽样从公开证据数据选取 300 条主样本，另加 30 条重测样本。抽样按平台、话题、机制、编码来源、纳入状态和文本长度分层，保证稀有标签也被覆盖。抽样使用固定随机种子，相同配置生成相同样本。

公开样本只保留盲测所需字段。当前标签、编码来源、复核状态和平台名称写入私有映射文件，不进入公开仓库。

## 三路独立代理

三名代理使用不同的判断结构，但共用同一套标签集合和定义：

- Reviewer A：严格依据编码手册分类，证据不足时保留 uncertain。
- Reviewer B：先概括主要诉求，再匹配标签。
- Reviewer C：先排除相邻标签，再做最终判断。

代理之间互不查看结果。代理只获得脱敏证据文本和可选父样本上下文，不会获得平台字段、来源编号、当前标签、编码来源和重测关系。公开脱敏文本按原貌保留。

文本中的“楼主”“评论区”等自然表达会保留，因为它们属于证据内容。

## 两种运行方式

运行器把两种方式明确分开，用参数 `--provider` 选择。

- **本地固定示例模式**（`--provider mock`，默认）：运行器按关键词生成确定性示例输出，用来跑通结构、解析和后续共识流程。它是结构自测，不是真实模型校准。此时报告标注 `result_type=mock_pipeline_self_test`、运行状态 `READY_NOT_RUN`，产物写入 `artifacts/calibration/mock_self_test/`。这里的一致率、标签熵和标签流向只用于验证流程能否跑通，不能作为真实模型校准结果、标签可靠性或 Codebook 质量结论。

- **真实模型模式**（`--provider openai_compatible`）：按 OpenAI 兼容接口调用外部模型。运行器从环境变量 `PSYLENS_LLM_BASE_URL`、`PSYLENS_LLM_API_KEY`、`PSYLENS_LLM_MODEL` 读取配置：base_url 表示接口地址，api_key 表示访问密钥，model 表示模型名称。Prompt 真实传入模型，temperature 与 seed 进入请求体，原始响应单独保存。解析失败进入 retry queue（重试队列），429、超时和网络错误按退避重试，支持断点续跑，运行器不记录密钥。此时报告标注 `result_type=real_agent_calibration`。

`result_type` 是结果类型标记，用来区分“结构自测”与“真实校准”。页面、README 和正式方法结论只引用真实校准结果，不引用本地固定示例模式的数值。

## 统计口径

共识报告给出三路完全一致率、多数一致率、两两一致率、话题与机制争议率、边界争议率、每个标签的一致率、重测一致率、当前标签与代理共识的混淆情况，以及不确定标签的流向。

报告在给出 Fleiss' Kappa、标签熵等指标时，同时附普通中文解释。Fleiss' Kappa 用来衡量三个代理的一致程度，并扣除随机碰巧一致的部分；标签熵用来衡量三路判断的分散程度，0 表示完全一致。

## 结果使用

一致的标签用于确认稳定结论。争议标签进入队列，作为标签边界校准的重点材料，并转化为 Codebook 改进提案。提案只是建议，不直接修改正式 Codebook。
