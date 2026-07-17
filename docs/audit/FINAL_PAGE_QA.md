# 最终页面 QA（FINAL_PAGE_QA）

> 展示页无障碍与响应式核查（静态审阅 + `tests/test_site_static.py`）。

## 结构与无障碍

| 项 | 结果 |
| --- | --- |
| skip link | 有（`.skip-link` 指向 #main） |
| heading 层级 | 单一 h1 + 分节 h2/h3（`test_single_h1`） |
| 语义化导航 | `<nav aria-label>`、`<main id="main">`、`<footer>` |
| 图片 alt | wordmark 有 alt="PsyLens" |
| 键盘操作 | 链接/按钮为原生 `<a>`，可 Tab 聚焦 |
| 对比度 | 深色背景 + 高亮文本（--text #e8ecf5 / --bg #0b0f1a） |
| prefers-reduced-motion | 有媒体查询关闭平滑滚动 |
| JS 失败可读 | 关键内容为静态 HTML，fetch 失败不影响阅读 |

## 响应式

| 断点 | 处理 |
| --- | --- |
| 桌面 | hero-stats 5 列 |
| 768px | hero-stats 2 列、导航紧凑 |
| 390px | hero-stats 1 列 |
| 横向溢出 | `overflow-x: hidden`；`.code` 可横向滚动 |

## 交互

- 无阻断式 Gate / ENTER / 滚动锁；
- 页面数字来自 `showcase.json`；
- 无能力映射、无招聘链接、无 source_url、无完整数据下载入口。

## 结论

页面满足高级视觉 + 普通语言表达 + 无障碍/响应式基本要求，静态测试全部通过。
