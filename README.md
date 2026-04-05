# PsyLens

多平台游戏社区反馈洞察工作流项目公开仓库。

当前公开案例以《英雄联盟》海克斯大乱斗模式为例，展示如何把公开社区反馈整理成主题、心理机制、证据链与行动建议。

## 仓库内容

- `docs/`：GitHub Pages 页面文件、公开结果文件、展示素材
- `docs/files/`：项目说明、整洁版输入、证据表、验证洞察、行动建议矩阵
- `docs/assets/`：页面图表与展示素材
- `scripts_public/`：公开版关键脚本

## 页面入口

GitHub Pages：`https://sherlock0717.github.io/PsyLens/`

## 公开仓库与完整执行包的关系

这个公开仓库主要用于：

1. 展示项目结构与结果
2. 提供公开版关键结果文件
3. 提供公开版关键脚本用于阅读、复用和二次开发参考

如果你想完整重跑项目，请使用本地执行包与私有数据环境，而不是只依赖当前公开仓库。

## How to use

### 1）先确认你在看什么

- 如果你的目标是**看项目结果**，优先看：
  - `docs/files/PsyLens_enterprise_project_brief_v3.docx`
  - `docs/files/input_feedback_phase2_multiplatform_clean.csv`
  - `docs/files/final_evidence_table.csv`
  - `docs/files/04_validated_insights.jsonl`
  - `docs/files/05_action_matrix.json`
- 如果你的目标是**理解脚本结构**，再看 `scripts_public/`

### 2）先用 `-h` 看参数

公开版脚本都采用命令行参数方式。建议先运行帮助，再决定怎么传参。

```powershell
python scripts_public/run_pipeline.py -h
python scripts_public/merge_phase2_inputs.py -h
python scripts_public/preclean_feedback_registry.py -h
python scripts_public/ai_curate_feedback.py -h
python scripts_public/crawl_tieba_selected.py -h
python scripts_public/crawl_bili_selected_auto.py -h
```

### 3）关键脚本最常用的参数是什么

#### `run_pipeline.py`

用于把整洁版输入进一步处理成证据表、验证洞察和行动建议矩阵。

常见参数：

- `--case`：case 配置文件路径
- `--mode`：`game` 或 `ux`
- `--input`：输入 CSV 路径
- `--review_provider`：可选复核模型提供方
- `--review_model`：可选复核模型名
- `--review_sample`：可选抽样复核数量

示例：

```powershell
python scripts_public/run_pipeline.py --case config/case_tencent_nga_lol_recent.yaml --mode game --input data/raw/input_feedback_phase2_multiplatform_clean.csv
```

#### `merge_phase2_inputs.py`

用于把多个平台的 AI 精修结果合并成统一字段结构，并按平台平衡样本。

常见参数：

- `--inputs`：一个或多个输入 CSV
- `--output`：输出 CSV
- `--per-platform`：每个平台保留多少条，默认 120

示例：

```powershell
python scripts_public/merge_phase2_inputs.py --inputs data/raw/feedback_registry_nga_ai.csv data/raw/feedback_registry_tieba_ai.csv data/raw/feedback_registry_bili_ai.csv --output data/raw/input_feedback_phase2_multiplatform_clean.csv --per-platform 120
```

#### `preclean_feedback_registry.py`

用于对 registry 文本做基础预清洗，去掉明显空白、图片路径、论坛 reply 头等噪声。

常见参数：

- `--input`：输入 registry
- `--output`：输出 preclean 文件

示例：

```powershell
python scripts_public/preclean_feedback_registry.py --input data/raw/feedback_registry_tieba.csv --output data/raw/feedback_registry_tieba_preclean.csv
```

#### `ai_curate_feedback.py`

用于对预清洗后的文本做 AI 精修，补充 `cleaned_text`、`keep_ai`、`theme_bucket`、`mechanism_prior`、`info_score` 等字段。

常见参数：

- `--input`：输入 preclean 文件
- `--output`：输出 AI 精修文件
- `--model`：可选模型名；默认读取环境变量

示例：

```powershell
python scripts_public/ai_curate_feedback.py --input data/raw/feedback_registry_tieba_preclean.csv --output data/raw/feedback_registry_tieba_ai.csv
```

#### `crawl_tieba_selected.py`

用于抓取贴吧 selected 帖子的正文与回复，并导出统一结构的 `feedback_registry_tieba.csv`。

常见参数：

- `--selected`：贴吧 selected CSV
- `--output`：输出 registry
- `--summary`：可选 summary 输出
- `--cookie-string` / `--cookie-file`：贴吧 cookie
- `--debug-html-dir`：保存 blocked / raw html，便于排错
- `--local-html-dir`：优先读取本地 html
- `--max-pages-per-thread`：每个线程最多抓多少页
- `--max-replies-per-thread`：每个线程最多保留多少条回复
- `--min-text-len`：最短文本长度
- `--sleep-sec`：请求间隔
- `--only-lz`：是否只看楼主

### 4）在本地完整执行包里怎么跑

当前项目本地根目录约定为：

```text
C:\Users\22358\Downloads\PsyLens_Execution_Pack_Tencent_GameCommunity
```

当前项目脚本目录约定为：

```text
C:\Users\22358\Downloads\PsyLens_Execution_Pack_Tencent_GameCommunity\scripts
```

如果你已经有完整执行包，可以直接在该目录下运行。

示例流程：

```powershell
cd C:\Users\22358\Downloads\PsyLens_Execution_Pack_Tencent_GameCommunity\scripts
python preclean_feedback_registry.py --input ..\data\raw\feedback_registry_tieba.csv --output ..\data\raw\feedback_registry_tieba_preclean.csv
python ai_curate_feedback.py --input ..\data\raw\feedback_registry_tieba_preclean.csv --output ..\data\raw\feedback_registry_tieba_ai.csv
python merge_phase2_inputs.py --inputs ..\data\raw\feedback_registry_nga_ai.csv ..\data\raw\feedback_registry_tieba_ai.csv ..\data\raw\feedback_registry_bili_ai.csv --output ..\data\raw\input_feedback_phase2_multiplatform_clean.csv --per-platform 120
python run_pipeline.py --case ..\config\case_tencent_nga_lol_recent.yaml --mode game --input ..\data\raw\input_feedback_phase2_multiplatform_clean.csv
```

### 5）运行前至少要准备什么

公开脚本会用到的常见 Python 包包括：

```powershell
pip install pandas pyyaml python-dotenv openai tqdm requests beautifulsoup4
```

如果你要运行 AI 精修或完整 pipeline，还需要准备对应环境变量，例如：

- `DEEPSEEK_API_KEY`
- `DEEPSEEK_BASE_URL`
- `DEEPSEEK_MODEL`
- 或 OpenAI 对应变量

### 6）怎么看公开仓库里的 scripts_public

`scripts_public` 更适合以下用途：

- 理解项目工作流怎么拆
- 看字段怎么标准化
- 看输入与输出接口长什么样
- 在你自己的项目里复用部分脚本逻辑

它不是“只下载公开仓库就一定能完整一键复现”的承诺版本。

## 关键结果文件说明

### `input_feedback_phase2_multiplatform_clean.csv`

三平台整洁版输入。当前公开版共 360 行，三平台各 120 行。

### `final_evidence_table.csv`

证据表。当前公开版共 697 个 evidence unit。

### `04_validated_insights.jsonl`

验证洞察文件。当前公开版共 19 条。

### `05_action_matrix.json`

自动生成的行动建议矩阵。对外表达时建议与人工修订版建议矩阵配合阅读。

## 当前公开结论

当前公开案例里，海克斯大乱斗的高频争议更稳定地指向**胜任受挫**：

- 玩家更常表达的是看不懂、打不顺、抓不住有效策略
- 公平威胁存在，但更集中在匹配、奖励与部分规则归因节点
- 队友互动与社区摩擦更像放大器，而不是唯一中心

## License

当前仓库用于项目展示、公开结果说明与方法结构参考。使用时请保留项目来源说明。
