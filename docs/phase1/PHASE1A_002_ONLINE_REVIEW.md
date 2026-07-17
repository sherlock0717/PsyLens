# Phase 1A-002 线上复核

## 结论

`8ab41940deb93b13cadb795eddbcb393b065606b` 已完成本轮主要加固：生成器测试隔离到临时目录、完整快照固定参数可复现、样本 ID 不受输入行重排影响、证据单元保留 legacy `_uN`、B 站队列与迁移表审计得到补强。

Phase 1A 的数据方向已经成立，但在进入 B 站正式标注前，还需完成一个收尾提交。当前不创建 PR、不合并 `main`、不修改 Pages。

## 已确认通过

1. 生成器核心函数接受 `output_dir`、`generated_at`、`source_data_commit` 和可选 `generator_commit`；测试使用 `tmp_path`，不再改写 tracked `data/v2/`。
2. 固定参数时，五个 CSV 与 manifest 共六个文件均进行字节级一致性测试。
3. `build_sample_ids` 按平台和 numeric legacy ID 排序，打乱输入后映射不变。
4. `unit_index` 保留 legacy `_uN`，并对同一 sample 下的索引冲突抛错。
5. manifest 使用 `source_data_commit` 和 POSIX 仓库路径。
6. B 站队列集合、状态、候选文本、索引连续性和迁移表分项已增加检查。

## 必须修复

### P0：`--csv-out` CLI 当前可能失效

`main()` 仍调用：

```python
write_linkage_csv(combined["legacy"], Path(args.csv_out))
```

但当前文件未保留可调用的 `def write_linkage_csv(...)`。原函数体片段位于 `run_combined_audit()` 的 `return out` 之后，属于不可达代码。

处理要求：

- 恢复独立的 `write_linkage_csv(result, path)` 函数；
- 删除 `return out` 后的不可达残留代码；
- 新增 CLI smoke test，实际运行 `--dataset legacy --csv-out <tmp_path>`；
- 因 legacy 状态仍为 BLOCKED，命令退出码可以为 1，但 CSV 必须成功生成且字段完整，不能抛 `NameError`。

### P1：`source_data_commit` 只检查非空，没有检查权威值

当前 `run_v2_audit()` 只要求 `manifest.source_data_commit` 非空。任意非空字符串都会通过该项检查。

处理要求：

- 为当前冻结 v2 快照定义权威来源提交：
  `371d245a0ce82ed5d980472147b49568525e2986`；
- `run_v2_audit()` 应验证 manifest 中的值与权威来源提交一致；
- 修改为其他非空值时，v2 审计必须 BLOCKED。

### P1：`source_files` 只检查格式，没有检查准确路径

当前审计确认其为 POSIX 相对路径，但没有验证是否正好指向：

- `docs/files/input_feedback_phase2_multiplatform_clean.csv`
- `docs/files/final_evidence_table.csv`

处理要求：对键集合和路径值做精确校验。

### P1：unit index 不变量只在 pytest 中校验

当前测试已经验证：

- `parse_legacy_unit_index == unit_index`；
- evidence ID 的 `U` 后缀与 unit_index 一致；
- sample + unit_index 无冲突。

但 `run_v2_audit()` 本身尚未把这些不变量纳入 `v2_migration_status`。

处理要求：将三项检查加入审计器，使手动篡改 `unit_index` 或 ID 后缀时，单独运行 `--dataset v2` 也会 BLOCKED。

## 建议补充的 CLI 测试

使用 subprocess 或直接调用 `main(argv)`，覆盖：

1. `--dataset legacy --csv-out <tmp>`：输出文件生成，退出码 1；
2. `--dataset legacy --mismatch-out <tmp>`：输出文件生成，退出码 1；
3. `--dataset v2 --json-out <tmp>`：JSON 生成，退出码 0；
4. 测试输出仅写入 `tmp_path`，不得改写仓库文件。

## 验收条件

完成上述修正后：

- 全部 pytest 通过；
- 三种数据集退出码仍为 `1 / 0 / 1`；
- 三类输出参数 smoke test 通过；
- pytest 前后 tracked `data/v2/` 不变；
- `run_v2_audit()` 能独立阻断错误来源提交、错误来源路径及 unit index 漂移；
- 不修改页面、README、`docs/files/**`、DOCX、`main` 或 Pages。
