# 最终链接审计（FINAL_LINK_AUDIT）

> 核查页面链接指向与 GitHub 文件路径。

## 页面链接

| 链接 | 目标 | 说明 |
| --- | --- | --- |
| GitHub 仓库 | `https://github.com/sherlock0717/PsyLens` | 有效 |
| README | `.../blob/phase1/rebuild-evidence-and-demo/README.md` | 指向当前工作分支 |
| 离线 Demo | `.../tree/phase1/rebuild-evidence-and-demo/demo` | 有效 |
| 评测方法 | `.../docs/evaluation/EVALUATION_METHOD.md` | 有效 |
| Codebook | `.../docs/methodology/MECHANISM_CODEBOOK.md` | 有效 |
| 完整抓取链 | `.../docs/pipeline/FULL_PIPELINE.md` | 有效 |

## 说明

- 页面仅含 GitHub 链接，无外部平台 URL、无 source_url（`test_no_source_url_or_full_download`）；
- 文件路径使用当前分支 `phase1/rebuild-evidence-and-demo`；合并 main 后（D-008）需将分支名更新为 main。
- 无指向数据文件（.csv/.jsonl）的下载链接。

## 待处理

- D-008 决定合并 main 后，页面 GitHub 文件链接的分支名应从 `phase1/rebuild-evidence-and-demo` 更新为 `main`（登记于决策包）。
