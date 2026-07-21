# 自动校准数据说明

这个目录保存自动校准流程的公开输入与公开样本。校准结果是自动校准参考，用于发现稳定结果和争议案例，不是人工金标准，也不覆盖公开数据的现有标签。

## 名词解释

- **证据单元**：从一条完整反馈中切出的、可以单独判断问题类型的短片段。
- **自动校准参考集**：由多个互不查看彼此结果的代理独立判断后形成的参考标签，用于发现稳定结果和争议案例。
- **盲测项**：去掉当前标签、编码来源、复核状态和平台名称后，交给代理判断的证据。

## 目录内容

| 文件 | 说明 |
| --- | --- |
| `calibration_sample.csv` | 公开分层校准样本，只含盲测所需字段，不含当前标签与平台字段 |
| `agent_review_schema.json` | 单个代理复检结果的字段结构 |

## 公开与私有边界

公开样本 `calibration_sample.csv` 只包含代理判断所需的盲测字段：

```
blinded_item_id, public_evidence_text, parent_context,
context_available, length_bucket
```

来源编号、平台名称、分层编码、重测关系，以及当前标签、体验机制、编码来源、复核状态和纳入状态，全部只写入 `artifacts/calibration/private_sampling_key.csv`：

```
blinded_item_id, source_evidence_id, platform_source, sampling_stratum,
is_retest, retest_group_id, current_surface_topic, current_mechanism_label,
label_source, review_status, analysis_inclusion_status
```

这样代理无法从公开样本反推来源、平台或哪些项是重复项。来源编号只在共识生成后，通过私有映射按 `blinded_item_id` 回填。该私有文件与原始模型响应都不进入公开仓库，已在 `.gitignore` 中排除。

## 生成方式

```bash
python tools/calibration/build_calibration_sample.py \
  --config config/calibration/calibration.yaml
```

抽样使用固定随机种子，相同配置生成相同样本。
