# 抓取指南（CRAWLING_GUIDE）

> 真实抓取**默认关闭**、需用户显式配置、**CI 永不运行**。本仓库不提供可直接批量抓取的开箱配置。

## 脚本

- `scripts_public/crawl_tieba_selected.py`：贴吧选定帖抓取；
- `scripts_public/crawl_bili_selected_auto.py`：B 站选定内容抓取。

## 运行前提（用户自行准备，切勿提交仓库）

- 遵守目标平台使用条款与 robots 规则；
- 控制频率、加入限速与重试；
- 登录态/Cookie 仅在本地使用，**不得提交**到仓库；
- 抓取结果先进入本地缓存，不直接入库。

## 安全红线

- 不提交 Cookie / Token / 账号 / 浏览器 profile / 登录缓存；
- 不在日志中打印凭据；
- 不做大规模再分发（见 `SECURITY_AND_PRIVACY.md`）。

## 离线替代

如仅需体验流程，使用离线 Demo：`python tools/run_demo.py`（不联网、不抓取）。
