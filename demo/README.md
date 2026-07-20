# 离线 Demo

输入少量脱敏反馈，Demo 会依次生成候选证据、确定性标签、草稿结构化洞察、待验证产品假设和评测报告。

## 默认设置

- **离线运行**：不联网、不访问平台、不调用外部模型；
- **无密钥依赖**：不读取 `.env`、Cookie 或 API Key；
- **独立输出**：只写入用户指定的 `artifacts/` 目录，不修改公开数据与项目说明；
- **确定性**：同一输入、配置和 run ID 产生相同输出。

## 运行

```bash
python tools/run_demo.py

python tools/run_demo.py \
  --input demo/examples/sample_feedback.csv \
  --output artifacts/demo/test_run

python tools/run_demo.py \
  --provider mock \
  --output artifacts/demo/ci
```

## 输出

运行目录包含：

- `input_snapshot.json`：输入快照与运行参数；
- `evidence.jsonl`：切分后的证据单元；
- `insights.jsonl`：按话题与机制组合形成的草稿观察；
- `actions.json`：带验证方法的产品假设；
- `evaluation.json`：结构和标签检查；
- `manifest.json`：产物数量与 SHA-256；
- `report.md`、`report.html`：可阅读报告。

## 目录

```text
demo/
  config/demo.yaml                 默认配置
  examples/sample_feedback.csv     脱敏示例输入
  mock/deterministic_responses.json 确定性规则
  prompts/                         提示词参考
  src/                             流程、校验、评分和报告\ n  tests/                           确定性与完整性测试
```

> 上述目录示意中的 `src/` 包含 pipeline、providers、validators、scoring 与 report 模块。
