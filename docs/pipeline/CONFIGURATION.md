# 配置说明

## 离线流程

公开数据规范化、分析汇总与 Demo 默认不需要环境变量：

```bash
python tools/normalize_public_dataset.py \
  --source-dir data/public \
  --output-dir artifacts/normalized_public

python tools/summarize_public_analysis.py \
  --public-dir data/public \
  --output artifacts/public_analysis_summary.json

python tools/run_demo.py --provider mock --output artifacts/demo/run
```

## Demo 配置

`demo/config/demo.yaml` 记录：

- `provider`：默认 `mock`；
- `min_unit_len`：候选证据最小长度；
- `offline`：是否强制离线。

命令行参数可以指定输入、输出、provider、run ID 与固定生成时间。

## 候选发现与平台配置

- `pipeline/config/case.example.yaml`：案例、主题、时间窗和输出字段；
- `pipeline/config/platforms.example.yaml`：平台类别、访问间隔和缓存策略示例；
- `pipeline/discovery/candidate_discovery_template.py`：只生成离线候选示例，不访问平台。

## 外部模型配置

`.env.example` 只列出可选变量：

- `PSYLENS_LLM_API_KEY`；
- `PSYLENS_LLM_BASE_URL`；
- `PSYLENS_LLM_MODEL`。

当前离线 Demo 不读取这些变量。接入外部模型时，需要单独实现 provider，并保持输入输出契约、标签白名单和错误处理一致。

## 真实采集配置

当前公开版本没有把历史页面抓取脚本标记为稳定入口。重新实现真实采集时，配置至少应包含：

- 目标平台与时间窗；
- 请求间隔、随机抖动和最大重试；
- 缓存目录与 checkpoint；
- 输出字段；
- 本地登录态位置；
- 失败日志位置。

Cookie、Token、API Key、账号密码和浏览器 profile 不能写入 YAML、日志或仓库。真实平台访问不进入 CI。
