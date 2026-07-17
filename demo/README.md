# PsyLens 离线 Demo

输入几条脱敏反馈，Demo 会生成：候选证据单元 → 确定性标签 → 草稿结构化洞察 → 待验证产品假设 → 评测报告。

## 默认行为

- **离线**：不联网、不调用模型、不运行抓取；
- **不读取** `.env` / Cookie / API Key；
- **不覆盖** `data/v2` 与 `docs/files`；
- **确定性**：同一输入与配置产生同样输出（有测试保障）。

## 运行

```bash
python tools/run_demo.py
# 或指定输入与输出
python tools/run_demo.py --input demo/examples/sample_feedback.csv --output artifacts/demo/test_run
# CI 使用 mock provider
python tools/run_demo.py --provider mock --output artifacts/demo/ci
```

## 输出（写入 artifacts/demo/<run_id>/）

`input_snapshot.json`、`evidence.jsonl`、`insights.jsonl`、`actions.json`、`evaluation.json`、`manifest.json`、`report.md`、`report.html`。

## 结构

```
demo/
  config/demo.yaml            配置（默认 mock、离线）
  prompts/                    真实运行时的提示词参考（Demo mock 不使用）
  examples/sample_feedback.csv 脱敏示例输入（无真实 URL/账号）
  mock/deterministic_responses.json 确定性 mock 标签规则
  src/                        pipeline / providers / validators / scoring / report
  tests/                      Demo 测试
```

## 关于真实 provider

`--provider real` 仅提供接口占位，默认不启用、**CI 永不运行**、需用户显式配置（见 D-010）。Demo 标签为演示用途，非人工复核结论。
