# Final Corrections 线上复核

## 结论

`3c803d0abd963812743531ef4aadac792468eacc` 已完成本轮绝大部分发布前修正：公开脱敏数据、规则基线重命名、评测指标重构、数据驱动 showcase、采集流程模板、正式 DOCX、测试与 CI 配置均已落盘。

当前可接受状态：

```text
engineering_completion   = COMPLETE_LOCALLY_WITH_MINOR_FIXES
remote_ci_status         = NOT_VERIFIED
public_release_readiness = PENDING_USER_DECISIONS
main_merge_status        = NOT_STARTED
pages_deployment_status  = NOT_STARTED
```

以下内容仅记录在审计与工程文档，不进入 README、展示页或正式 DOCX 主体。

## 已确认通过

1. README 与页面未堆叠 P0/P1/BLOCKED 等内部阻断语言。
2. B 站标签已准确改称“离线规则基线提案”。
3. `data/public/**` 不含 `source_url`，正式 public manifest 已记录字段和哈希。
4. 正式 `PsyLens_project_brief.docx` 已存在，旧 v3/v4 已归档。
5. 页面删除 Gate、能力映射、招聘链接，并使用自然语言区分结构校验、标签待复核和规则基线。
6. Ruff 已改为 CI 阻断项；本地报告为 113 passed、Ruff 0 告警。
7. 草稿洞察和行动假设仍默认隐藏，未伪造人工复核。

## 必须完成的两个小型工程修正

### 1. repeatability_rate 没有遵循 evaluator 的 input_dir

`tools/evaluate_v2.py` 的 `_compute_repeatability()` 调用 `build_provisional_evidence.build()`，但该生成器仍固定从仓库 `data/v2` 读取输入。因而：

- evaluator 的其他指标可由 `--input-dir` 控制；
- repeatability_rate 实际总是针对仓库固定数据，而非传入的 input_dir；
- 临时目录篡改测试无法验证对应输入的可重复性。

修正要求：

1. `build_provisional_evidence.build()` 增加 `input_dir` 参数；
2. samples/evidence/proposals/ambiguous 全部从 input_dir 读取；
3. `_compute_repeatability(input_dir)` 显式传入 evaluator 的输入目录；
4. 测试复制并修改临时输入，确认重复性计算针对该临时数据；
5. CLI 默认行为保持不变。

### 2. HTML 仍保留硬编码案例数字

`docs/index.html` 的静态回退和案例段仍直接写有：

- 样本 360；
- 平台 3；
- 每平台 120。

虽然 JS 会从 showcase.json 覆盖部分数字，但这仍不满足“页面关键数字由数据生成”的严格口径。

修正要求：

- 静态 `<dd>` 使用 `—` 或无数字占位；
- 案例说明中的 360/120 使用 data-showcase 节点注入，或由构建器生成；
- JS 失败时使用不含具体数字的自然语言回退；
- 新增测试，确保 HTML 正文不硬编码 360、120、927、695、279、2 等项目计数。

## 发布前仍需确认

1. 当前没有远程 GitHub Actions 运行证据，Ubuntu/Windows 仍为 NOT_VERIFIED；
2. `data/v2` 与历史提交仍含来源字段，最终 main 合并范围必须按 D-001/D-002 决定；
3. 页面文档链接当前指向 phase1 分支，合并 main 时应使用 `--repo-ref main` 重建。

## 验收条件

完成上述两个小修后：

- 本地 compileall / Ruff / pytest 全部通过；
- evaluator 临时输入隔离测试通过；
- HTML 无硬编码项目计数；
- public 数据仍无来源 URL；
- 正式 DOCX 仍可读；
- 取得 Ubuntu 与 Windows CI 运行证据，或继续明确标记 NOT_VERIFIED；
- 不修改 README/page 的简洁公开表达，不把内部审计问题写入公开主体。
