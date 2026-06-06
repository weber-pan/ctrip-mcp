# ctrip-mcp (携程 MCP - 真抓版)

> 配套姊妹仓库:[xiecheng-mcp](https://gitee.com/weber-pan/xiecheng-mcp)(wendao LLM 兜底版)
> 配套 Agent skill: [`ctrip-product-research`](devops/ctrip-product-research) umbrella → [`ctrip-spa-capture`](devops/ctrip-spa-capture) + [`ctrip-product-report`](devops/ctrip-product-report)

把携程 m 端 h5 SPA 内部 graphql/soa 接口封装为 [Model Context Protocol](MCP) server。
**核心差异**:不走携程"问道"LLM 兜底,直接 Playwright 跑 chromium + fetch hook 拦截 SPA 内部接口,拿到一手 JSON。

## 状态 Badge

<!-- status badges -->
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
![MCP](https://img.shields.io/badge/MCP-2025--06--18-green)
![Chromium Required](https://img.shields.io/badge/chromium-required-orange)
![License: MIT](https://img.shields.io/badge/license-MIT-lightgrey)
<!-- /status badges -->

## 为什么需要这个仓库

| 路径 | 数据质量 | 风险 |
|---|---|---|
| 携程 PC/H5 端 curl | ❌ 403/404(纯 CSR 壳) | 拿不到任何数据 |
| wendao LLM 兜底([xiecheng-mcp](https://gitee.com/weber-pan/xiecheng-mcp)) | ⭐⭐⭐ LLM 复述 | **串台**(问 p64158367 沙巴 → 给 p71068823 重庆) |
| **本仓库 Playwright 真抓** | ⭐⭐⭐⭐⭐ 真实 JSON | 需 chromium,抓取约 25s/产品 |

**结论**:**双轨并用** — 优先本仓库(真抓),失败/跨产品比对用 wendao 兜底。

## 在三 skill 拓扑中的位置

```
┌────────────────────────────────────────────────────────┐
│ ctrip-product-research    (umbrella / index / 路由)     │
│ 用户发携程 URL → 路由到 ↓                                │
└────────────────────────────────────────────────────────┘
       ↓ 抓数据                ↓ 拼报告
┌─────────────────┐    ┌─────────────────┐
│ ctrip-spa-capture│   │ctrip-product-report│
│  (技术层)        │    │  (工作流层)         │
│  Playwright      │    │  7 段式报告        │
│  fetch hook      │    │  字段对照表         │
│  8 个 graphql    │    │  4 线路逐线抓流程  │
└────────┬────────┘    └─────────────────┘
         │ 同一份代码库
         ↓
┌────────────────────────────────────────────────────────┐
│ ★ ctrip-mcp (本仓库)  MCP server 化                    │
│ 5 个工具,跨 MCP 客户端                                  │
│ (Claude Desktop / Continue / Cline / mcphub 任何端)    │
└────────────────────────────────────────────────────────┘
         ↑ 姊妹项目
┌────────────────────────────────────────────────────────┐
│ xiecheng-mcp  (wendao LLM 兜底版, 不用 chromium)        │
└────────────────────────────────────────────────────────┘
```

**优先级**:
1. **ctrip-mcp(本仓库)** — 跨 MCP 客户端,5 个工具,首选
2. **ctrip-spa-capture skill** — Agent 内部自己跑,产物与 MCP 一样
3. **wendao / xiecheng-mcp** — LLM 兜底,串台时验证

## 工具列表 (Tools)

| 工具 | 说明 | 底层接口 |
|---|---|---|
| `ctrip_spa_capture` | 抓取携程 m 端 h5 SPA 真实 graphql/soa body | Playwright + chromium + fetch hook |
| `ctrip_get_product` | 解析 4 条线路/价格日历/酒店/点评(用 `ctrip_spa_capture` 产物) | 本地 JSON 解析 |
| `ctrip_compare_subproducts` | 对 4 个 sub-productId 各跑一次抓取,补齐 B/C/D 行程 | `ctrip_spa_capture` 多次 |
| `ctrip_get_hotel_price` | 查某酒店 7/4-7/9 真实房型+价(走 AI_Go_Hotel_MCP 适配) | MCP 直转 |
| `ctrip_health` | 健康检查 — chromium 在不在、产物目录可写 | 本地 |

## 端到端测试结果(2026-06-06 沙巴产品 64158367)

```
=== 1) ctrip_spa_capture ===
duration: 15.16s
xhrs count: 11
  saved getCommentSummary / getByRelationId / getPromotionTag
  saved ProductInfo_2nd_V3_h5 / VPC_SelectDateProductInfo_h5
  saved batchPriceCalendar / ProductInfo_VisaInfo_h5
  saved dom / screenshot

=== 2) ctrip_get_product ===
  name: 马来西亚沙巴 7 日 5 晚私家团
  min_price: ¥5763 (orig ¥5798) on 2026-06-24
  lines: 4
    - subId=64158367 sort=1  3+2 组合，双酒店随心任选
    - subId=38789419 sort=2  高端升级--2晚丹绒香格里拉
    - subId=73810124 sort=3  2 晚热销+3晚海滨度假酒店
    - subId=73810123 sort=4  全程同酒店入住，无需舟车劳顿
  hotels: 8
  comments: scoreAvg=4.8 count=1
  price_calendar dates: 252
    全月最低: 2026-09-07 ¥4849 (line 3+2 组合)

=== 3) 7/4 班期价 (4 条线) ===
  subId=64158367  ¥6857  3+2 组合
  subId=38789419  ¥8365  高端升级
  subId=73810124  ¥7360  2晚热销+3晚海滨
  subId=73810123  ¥6905  全程同酒店
```

## 安装 (uv,推荐)

```bash
git clone https://gitee.com/weber-pan/ctrip-mcp.git
cd ctrip-mcp
uv sync                                          # 一键装依赖
playwright install chromium                       # 装 chromium (~150MB)
                                                    # 或用系统已有: ~/.cache/ms-playwright/chromium-1223/chrome-linux64/chrome
ctrip-mcp                                          # 跑 server (stdio 模式)
```

## 接入 MCP 客户端

详细见 [`docs/MCPHUB_INTEGRATION.md`](docs/MCPHUB_INTEGRATION.md)。**最快路径** — mcphub web UI 手动加 1 个 stdio server:

| 字段 | 值 |
|---|---|
| Name | `ctrip` |
| Command | `/opt/hermes/.venv/bin/python` |
| Args | `-m ctrip_mcp.server` |
| Workdir | `/opt/data/ctrip-mcp`(git clone 路径) |
| Env | `CTRIP_DATA_DIR=/opt/data/ctrip-data`(可选) |

## 端到端测试

```bash
# 1) 工具列表 + 健康检查
/opt/hermes/.venv/bin/python scripts/test_server.py

# 2) 真抓产品 + 解析 + 7/4 班期价
/opt/hermes/.venv/bin/python scripts/test_e2e.py
# 输出会显示 xhrs / saved files / 4 lines / 7/4 prices
```

## 关键 graphql 接口

| 接口 | 拿什么 |
|---|---|
| `ProductInfo_2nd_V3_h5` | 4 条线路 groupCard、8 家酒店、点评汇总、行程 |
| `VPC_SelectDateProductInfo_h5` | 4 个 sub-productId、7 月全月分价(252 天)、签证、班期规则 |
| `ProductInfo_VisaInfo_h5` | 签证详情 |
| `batchPriceCalendar` | 价格日历(优惠明细) |
| `getCommentSummary` | 真实用户点评分 |

**真实 endpoint**: `https://m.ctrip.com/restapi/soa2/18055/graphql?queryName=<MethodName>`

method 名在 `queryName=` query string 里(URL 路径末尾是字面 "graphql")。

## 与姊妹项目对比

| | ctrip-mcp (本仓库) | xiecheng-mcp |
|---|---|---|
| 数据源 | 携程 m 端 graphql | wendao LLM |
| 速度 | 15-25s/产品 | 10-30s/query |
| 准确度 | ⭐⭐⭐⭐⭐ 真实 JSON | ⭐⭐⭐ LLM 复述 |
| 串台风险 | ❌ 无 | ⚠️ 有 |
| 需要 token | ❌ | ✅ |
| 需要 chromium | ✅ (~150MB) | ❌ |
| 跨 MCP 客户端 | ✅ | ✅ |

**两个都装,优先 ctrip-mcp(真抓),wendao 兜底**。

## Pitfall 日志(开发踩坑)

- **Playwright `resp.text()` 拿不到 graphql body** — 用 `add_init_script` hook `window.fetch` + `XMLHttpRequest.send`
- **on_response handler 时机** — 先 `page.on("response", cb)`,再 `page.goto`
- **URL tag 提取优先 `queryName=`** — graphql 统一端点,method 名在 query string 里
- **容器没 chrome 别再 `npx playwright install`** — 用 `~/.cache/ms-playwright/chromium-1223/chrome-linux64/chrome` 现成二进制
- **真抓要滚动到底部** — SPA lazy load,D3 之后不滚拿不到

详见 [`references/ctrip-spa-graphql-hook.md`](references/ctrip-spa-graphql-hook.md) 和 [`references/csr-spa-capture-technique.md`](references/csr-spa-capture-technique.md)(后者 generalizable, 微博/小红书/美团/抖音 SPA 都可改改用)。

## License

MIT
