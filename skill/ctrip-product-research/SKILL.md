---
name: ctrip-product-research
description: 携程产品研究的**导航/索引 umbrella** — 拿到携程产品相关任务时,本 skill 帮你**选合适的子 skill**,不重复实现。触发: 用户发携程 URL、提到 p<productId>、问"几条线路""每天行程""点评分""优缺点""完整价格日历""城市字典""图片下载"。**请先加载下面两个子 skill,本 skill 只做路由**。

# 携程产品研究 — 导航

收到携程产品相关任务时,按下方路由表加载子 skill。

## 路由表

| 用户问 | 路由 |
|---|---|
| 真实数据 / 原始 JSON / 串台 / 数据源 | `ctrip-spa-capture` |
| 行程 / 点评 / 优缺点 / 7 段式报告 | `ctrip-product-report` |
| 调 MCP / 跨客户端 (Claude Desktop, mcphub) | `ctrip-mcp` (gitee) |
| 单点酒店房价 / 房型 | `AI_Go_Hotel_MCP` (mcphub) |
| 天气 (国内/≤4 天) | `amap-mcp-maps_weather` |
| 天气 (7/4 远期预测, 风险告知) | `wendao-skill` |
| 出发机票 | `variflight-mcp` (mcphub) |

## 怎么开始

**Step 1**: 用户给链接,先看 URL:
- 携程 m 端 h5: `https://m.ctrip.com/webapp/vacations/tour/detail?productId=XXX&departCityId=YYY` ← 主抓路径
- 携程 pc: `https://vacations.ctrip.com/travel/detail/pXXX/?city=YYY&rv=1` ← 改 m 端 URL

**Step 2**: URL 提取 `productId` + `city`(国内出发城市 ID)

**Step 3**: 跑 `ctrip-spa-capture/scripts/ctrip_spa_capture.py <pid> <city>` 抓原始数据

**Step 4**: 跑 `ctrip-spa-capture/scripts/extract_more.py <pid>` 提取 11 段"被遗忘字段"

**Step 5**: 加载 `ctrip-product-report` 拼 7 段式报告(模板见子 skill)

## city 字典(国内出发城市 ID)

| ID | 城市 | ID | 城市 |
|---|---|---|---|
| 1 | 北京 | 17 | 杭州 |
| 2 | **上海** | 28 | 成都 |
| 3 | 天津 | 30 | 深圳 |
| 5 | 哈尔滨 | 32 | 广州 |
| 12 | 南京 | 1244 | 重庆 |

完整 68 城在 `DepartureCityPriceList[]` 里(抓取后查看)。

## 11 段"被遗忘"模板

详见 `ctrip-spa-capture` SKILL.md 第 3 节。

## 子 skill

- [`ctrip-spa-capture`](./ctrip-spa-capture/SKILL.md) — Playwright 真抓 m 端 h5 SPA
- [`ctrip-product-report`](./ctrip-product-report/SKILL.md) — 拼装 7 段式报告

## 下游

- `ctrip-mcp` (gitee.com/weber-pan/ctrip-mcp) — 跨 MCP 客户端工具
