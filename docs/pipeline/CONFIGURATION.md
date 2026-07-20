# 配置说明（CONFIGURATION）

## 环境变量（.env.example）

- 默认离线运行不需要任何环境变量；
- 真实 provider（可选）：`PSYLENS_LLM_API_KEY` / `PSYLENS_LLM_BASE_URL` / `PSYLENS_LLM_MODEL`；
- 真实抓取（可选）：`PSYLENS_ENABLE_CRAWLER`（默认 false）。
- 切勿把真实 Key/Token/Cookie 提交仓库。

## Demo 配置（demo/config/demo.yaml）

- `provider`：mock（默认）| real；
- `min_unit_len`：候选单元最小长度；
- `offline`：强制离线。

## legacy 脚本配置（当前缺失）

legacy `scripts_public/**` 运行需要 `config/case_*.yaml`、`prompts/` 与第三方依赖（pandas/openai/requests/bs4），这些**未纳入公开仓库**（见 `FULL_PIPELINE.md` 缺失项）。如需真实运行需自行补齐并遵守平台条款。
