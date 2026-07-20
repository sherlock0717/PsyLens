# 最终隐私审计（FINAL_PRIVACY_AUDIT）

> 准确区分公开层、公开数据副本、内部迁移文件与历史提交四种范围。底层历史数据不删除，未重写历史。

## 分层结论（准确表述）

| 范围 | 是否含原始 URL | 说明 |
| --- | --- | --- |
| 1. 展示页（docs/index.html、showcase.json） | 否 | 页面仅含仓库自身 GitHub 链接；无 source_url、无完整数据下载入口 |
| 2. 公开数据副本（data/public/**） | 否 | 由 `tools/build_public_dataset.py` 生成，移除 source_url 与身份定位字段，SHA-256 记录于 public_manifest |
| 3. 内部迁移文件（data/v2/samples_v2.csv 等） | 是 | 仍保留来源字段，供内部审计/迁移可核查；不进入发布合并范围（见 RESTRICTED_DATA_FILES.md） |
| 4. 历史 Git 提交 | 可能是 | 历史提交中已存在含 URL 的旧数据；删除当前文件不能消除历史可访问性 |
| 5. 历史重写 | 未执行 | 本任务不重写 Git 历史、不 force push |

## 检查结果（公开层与公开数据副本）

| 项 | 结果 |
| --- | --- |
| 展示页无 source_url | 通过（`test_no_source_url_or_full_download`） |
| showcase.json 仅含仓库自身 URL | 通过（`test_showcase_json_no_secrets`） |
| public 数据副本无 source_url / 无 URL | 通过（`test_public_dataset`：无 http/https、无账号字段） |
| public 哈希与 manifest 一致 | 通过（`test_public_hashes_match_manifest`） |
| Demo 数据无真实 URL | 通过（`demo/examples/sample_feedback.csv` 脱敏） |
| pipeline 示例无真实 URL | 通过（`test_pipeline_templates`） |
| 无邮箱/电话/QQ/微信/Cookie/Token/Key | 通过（脱敏正则 + `test_no_real_secret_format_in_tracked_text`） |
| 页面不提供完整数据下载 | 通过（无 .csv/.jsonl/download 入口） |

## 待决策（不阻断其他工作）

- **D-001**：含来源字段的内部数据是否继续保留在未来 main（推荐：仅合并 data/public）；
- **D-002**：历史提交中的来源 URL 是否需要后续单独清理（推荐：暂不重写历史，发布只用 data/public）。

## 处理原则

- 底层历史数据（`docs/files/**`、`data/v2/**`）不删除；
- 公开页面、公开数据副本、Demo、示例中不出现原始 URL 与可识别信息；
- 历史可访问性问题如实记录，未做历史重写；争议项进入延期决策。
