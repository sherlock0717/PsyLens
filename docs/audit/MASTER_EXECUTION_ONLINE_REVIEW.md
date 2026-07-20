# Master Execution 线上复核

## 结论

`bf15a86a1354c9cba8c4c3e1ae3d51a5d12deb8c` 已完成大量有效工程工作：稳定 ID、legacy 证据迁移、B 站候选队列、规则基线提案、provisional 证据、草稿洞察与行动假设、离线 Demo、README、展示页、CI/Pages workflow 和最终决策包均已落盘。

但当前不能写作：

```text
engineering_completion = COMPLETE
```

更准确的状态是：

```text
engineering_completion = NEEDS_FINAL_CORRECTIONS
public_release_readiness = BLOCKED
main_merge_status = NOT_STARTED
pages_deployment_status = NOT_STARTED
```

在以下问题修正前，不创建发布 PR、不合并 main、不部署 Pages。

---

## 已确认通过

1. 分支相对 main 向前 27 个提交，main 未修改。
2. 360 条样本、695 条唯一迁移证据、2 条歧义证据、279 条 B 站候选、927 条 provisional 证据等产物已经落盘。
3. human review 日志没有伪造真人复核，当前只有 system_migration 事件。
4. 草稿洞察和行动假设均默认 `hidden_pending_review`。
5. 页面已删除阻断式 Gate、能力映射和招聘链接，保留品牌化 Hero。
6. 离线 Demo、CI workflow 和 Pages workflow 已建立。
7. README 明确说明人工复核覆盖为 0，未把草稿写成正式结论。

---

## P0 发布阻断项

### P0-1：公开数据与 URL 的隐私结论不成立

仓库当前为 public。`data/v2/samples_v2.csv` 和 legacy `docs/files/**` 均可从公开分支直接下载，`samples_v2.csv` 中包含完整 `source_url`。

因此以下表述不准确：

- “完整数据下载默认不开放”；
- “底层保留、公开层隐藏”；
- “公开层无 source_url”。

页面不提供链接，只能隐藏入口，不能阻止公开仓库文件被下载。

处理要求：

1. 将 D-001/D-002 重写为“仓库文件是否继续公开分发”，而非“页面是否显示入口”；
2. 明确历史 Git 提交中已存在 URL，删除当前文件不能消除历史可访问性；
3. 在用户决策前，至少生成不含 URL 的公开 v2 数据副本，并将含 URL 数据标记为不可进入发布分支；
4. FINAL_PRIVACY_AUDIT 不得再判定“公开层无 URL”全面通过。

### P0-2：完整抓取链尚未公开完整

`docs/pipeline/FULL_PIPELINE.md` 明确列出当前缺失：

- 候选发现脚本；
- 真实运行 prompts；
- `config/case_*.yaml`；
- 真实示例输入；
- legacy mock/dry-run；
- legacy 第三方依赖声明。

这与用户已确定的“完整抓取链需要公开”不一致。文档说明缺失项不能等同于完成公开。

处理要求：

- 补齐可安全公开的脚本、Prompt、配置模板、依赖和最小示例；
- 无法恢复的部分必须明确标记为历史不可复现，而不能称“完整抓取链已公开”；
- README、最终报告和页面应使用准确口径。

### P0-3：页面“评测状态 PASS”过强

页面 Hero 直接展示 `evaluation_status=PASS`，但同一评测报告同时显示：

- `parent_semantic_linkage_rate=0.0`；
- `human_review_coverage=0.0`；
- `low_support_claim_rate=0.6071`；
- legacy_status=BLOCKED；
- publication_readiness=PENDING_USER_DECISIONS。

裸露的 PASS 容易被理解为分析质量或项目发布已经通过。

处理要求：

- 页面改为“结构校验通过 / 标签待人工复核”；
- 分开展示 migration、provisional、human review、publication 四种状态；
- `human_review_coverage=0` 不得判定为 pass，应为 `not_started` 或 warning；
- 总体状态不得只由“无 block 阈值”生成一个 PASS。

### P0-4：页面数字并未真正全部数据驱动

`tools/build_showcase_data.py` 仍硬编码：

- sample_count=360；
- platform_count=3；
- migrated_evidence=695；
- bili_candidates=279；
- unresolved_ambiguous=2；
- legacy/v2/provisional/human/publication 状态。

其中 `sample_count` 还使用了永远返回 360 的表达式。现有测试只检查 HTML fetch 了 showcase.json，没有检查 showcase 数字是否从源文件复算。

处理要求：

- 所有计数与状态从 manifest、CSV、审计结果和 decision register 计算；
- 测试逐项篡改临时源数据并验证 showcase 输出随之变化；
- 删除 `or True` 等无效断言；
- 页面不得将硬编码 JSON 包装成“数据驱动”。

---

## P1 工程与方法问题

### P1-1：“Agent 提案”实际是关键词规则基线

`tools/build_review_infra.py` 使用固定关键词和优先级生成 279 条标签，不是 LLM Agent 的逐条语义判断。

处理要求：

- 全部公开表述改成“离线规则基线提案”或 `rule_based_proposal`；
- `label_source` 不再写 `agent_proposed`，除非后续确实由模型/人工 Agent 完成；
- 草稿洞察与建议的限制中明确它们建立在规则基线 + legacy AI 标签之上。

### P1-2：评测器没有实现其声明的完整指标

`evaluation/metrics.yaml` 定义但 `tools/evaluate_v2.py` 未计算或未真实计算的指标包括：

- platform_coverage；
- time_window_coverage；
- stage_completion_rate；
- repeatability_rate；
- parse_success_rate 当前硬编码为 1；
- human_review_coverage / human_override_rate 当前硬编码；
- manifest_completeness 只判断文件存在。

同时 `--output-dir` 参数没有控制输入和最终写入目录，仍使用固定 `V2_DIR`。

处理要求：

- 指标要么真实计算，要么从正式指标清单移除；
- 所有比例记录真实分子/分母；
- `--output-dir` 应真实生效并支持 tmp_path 测试；
- 评测报告必须区分 structural integrity、label quality、insight quality 和 release readiness。

### P1-3：正式 DOCX 与唯一入口仍未完成

用户此前已确定：比较 v3/v4 后只保留一个正式入口。当前只生成 Markdown 底稿，v3/v4 仍未归档，正式 DOCX 不存在。

这不只是发布选择，也是未完成交付物。

处理要求：

- 基于新 README 和页面生成 `PsyLens_project_brief.docx`；
- 将 v3/v4 归档；
- README 和页面只链接一个正式入口；
- 用户可决定是否在页面突出展示，但不需要再次决定是否生成。

### P1-4：远程 CI 尚未独立验证

当前 commit 没有可见的 GitHub Actions status/check，无法确认 Ubuntu 和 Windows 实际通过。Agent 报告中的 77 passed 属本地结果。

处理要求：

- 创建非发布 Draft PR 或手动触发 CI；
- Ubuntu 与 Windows 均成功后才可声称跨平台 CI 通过；
- Ruff 不应 `continue-on-error: true`，否则静态检查不构成门槛。

### P1-5：页面及最终报告仍有若干口径问题

- `source_url_coverage=1.0` 只证明字段非空，不能表述为“能追到原帖”；
- 页面“可核查证据 927”应注明其中 163 条为 uncertain flagged、全部未经人工复核；
- 页面链接仍指向 phase1 分支，合并前正常，发布前必须切换到 main；
- 使用 `innerHTML` 渲染 showcase 文案没有必要，应使用 `textContent`/DOM 节点，避免未来数据文本引入 HTML。

---

## 测试体系需要补强

1. `tests/test_site_static.py` 存在 `... or True`，该断言实际永远通过；
2. 页面数据驱动测试只检查 fetch 存在，没有验证数字来源；
3. CI guard 只比对 showcase 与 evaluation 的 evaluation_status；
4. 需要增加公开仓库文件级 URL/PII 扫描，而非只扫描页面和 Demo；
5. 需要增加 evaluator 临时目录隔离与重复运行测试；
6. 需要增加 rule-based proposal 与人工/模型 proposal 的状态区分测试。

---

## 修正后的状态建议

```text
phase1_data_migration        = PASS
provisional_structure        = PASS
label_quality_validation     = NOT_STARTED
human_review_status          = NOT_STARTED
full_pipeline_publication    = INCOMPLETE
remote_ci_status             = NOT_VERIFIED
formal_docx_status            = NOT_CREATED
privacy_release_status       = BLOCKED
engineering_completion       = NEEDS_FINAL_CORRECTIONS
public_release_readiness     = BLOCKED
```

## 下一步顺序

1. 修正公开数据/URL 策略与隐私报告；
2. 补齐或准确降级完整抓取链；
3. 修正评测器和页面状态语义；
4. 让 showcase 真正数据驱动；
5. 将规则提案重新命名；
6. 生成正式 DOCX 并归档旧版；
7. 运行远程 Ubuntu/Windows CI；
8. 再进行最终 PR 与 Pages 发布决策。
