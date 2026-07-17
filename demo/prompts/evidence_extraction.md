# Prompt 参考：证据抽取（evidence_extraction）

> 仅供真实 provider 运行时参考；Demo 默认 mock 不使用本文件。

任务：从一条社区反馈原文中切出语义独立、可单独判断话题与机制的证据单元。

要求：
- 每个证据单元的文本必须逐字来自原文，不改写、不补全；
- 过短或纯语气/连接片段不作为独立证据；
- 输出每个单元的 unit_text 与其在原文中的位置线索（evidence_phrase）。

输出格式（JSON）：
```json
{"units": [{"unit_text": "...", "evidence_phrase": "..."}]}
```
