# 失败与恢复（FAILURE_RECOVERY）

## 抓取阶段（真实运行，默认关闭）

- **限速/反爬**：加入退避重试；命中限制时暂停并从缓存 resume；
- **登录失效**：本地重新登录，不提交登录态；
- **部分失败**：以候选清单为 checkpoint，仅补抓失败项。

## 离线阶段（可复现）

- **解析失败**：审计器 `parse_success_rate` 会报告；修正数据后重跑；
- **哈希不一致**：`output_hash_match_rate` / manifest 校验会阻断；重生成快照；
- **标签非法/引用不可解析**：评测器标记 block，需修正后重跑。

## Demo

- Demo 确定性：同输入同输出；若哈希漂移，检查是否误改示例或 mock 规则；
- Demo 失败退出码非 0（评测 BLOCKED），CI 会捕获。

## 数据保护

- 生成脚本写入 `data/v2/**` 或 `artifacts/**`，**不覆盖** `docs/files/**` 历史数据；
- 正式 v2 快照用固定 `generated_at` + `source_data_commit` 重生成，保证可复现。
