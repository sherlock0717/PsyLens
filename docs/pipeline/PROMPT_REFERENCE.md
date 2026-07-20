# Prompt 参考

离线 Demo 使用确定性 mock provider，不调用提示词。`pipeline/prompts/` 与 `demo/prompts/` 提供接入外部模型时的输入输出参考。

| 阶段 | 主要文件 | 目标 |
| --- | --- | --- |
| 证据抽取 | `pipeline/prompts/evidence_extraction.md` | 从完整反馈中抽取可独立判断且可回溯的证据单元 |
| 表层话题编码 | `pipeline/prompts/topic_coding.md` | 从固定 codebook 中选择主要具体话题 |
| 体验机制编码 | `pipeline/prompts/mechanism_coding.md` | 从固定心理机制中选择主要体验方向 |
| 洞察生成 | `pipeline/prompts/insight_generation.md` | 按话题、机制、平台和证据组合形成结构化观察 |
| 产品假设 | `pipeline/prompts/action_generation.md` | 将证据支持的观察转为带验证方法的产品假设 |
| 人工整理 | `pipeline/prompts/curation.md` | 记录保留、修改、合并和排除理由 |

## 通用约束

- 标签取值严格限定于 codebook；
- 证据文本必须能够在输入样本中定位；
- 信息不足时使用 `uncertain` 或 `other_uncertain`；
- 每条输出保留来源样本或证据 ID；
- 区分机制不确定与证据纳入提醒；
- 不把模型置信度解释为证据强度；
- 不把频率直接解释为因果或问题严重度；
- 产品假设需要包含目标用户、干预内容、验证方法和成功指标；
- 禁止使用“已验证”“可直接采信”“应立即实施”等超出证据范围的表述。

## 结果校验

模型输出进入公开数据前需要经过：

1. JSON 或表格解析；
2. 字段白名单检查；
3. 标签合法性检查；
4. 来源 ID 解析；
5. 证据文本回溯；
6. 重复与不确定分布检查；
7. 小规模人工抽查与争议记录。

Prompt 只定义模型任务接口，最终质量由数据规则、评测脚本和复核记录共同控制。
