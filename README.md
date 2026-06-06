# ctrip-mcp (携程 MCP - 真抓版)

> 配套姊妹仓库:[xiecheng-mcp](https://gitee.com/weber-pan/xiecheng-mcp)(wendao LLM 兜底版)

把携程 m 端 h5 SPA 内部 graphql/soa 接口封装为 [Model Context Protocol](MCP) server。
**核心差异**:不走携程"问道"LLM 兜底,直接 Playwright 跑 chromium + fetch hook 拦截 SPA 内部接口,拿到一手 JSON。

## 为什么需要这个仓库

| 路径 | 数据质量 | 风险 |
|---|---|---|
| 携程 PC/H5 端 curl | ❌ 403/404(纯 CSR 壳) | 拿不到任何数据 |
| wendao LLM 兜底([xiecheng-mcp](https://gitee.com/weber-pan/xiecheng-mcp)) | ⭐⭐⭐ LLM 复述 | **串台**(问 p64158367 沙巴 → 给 p71068823 重庆) |
| **本仓库 Playwright 真抓** | ⭐⭐⭐⭐⭐ 真实 JSON | 需 chromium,抓取约 25s/产品 |

**结论**:**双轨并用** — 优先本仓库(真抓),失败/跨产品比对用 wendao 兜底。

## 工具列表 (Tools)

| 工具 | 说明 | 底层接口 |
|---|---|---|
| `ctrip_spa_capture` | 抓取携程 m 端 h5 SPA 真实 graphql/soa body | Playwright + chromium + fetch hook |
| `ctrip_get_product` | 解析 4 条线路/价格日历/酒店/点评(用 `ctrip_spa_capture` 产物) | 本地 JSON 解析 |
| `ctrip_compare_subproducts` | 对 4 个 sub-productId 各跑一次抓取,补齐 B/C/D 行程 | `ctrip_spa_capture` 多次 |
| `ctrip_get_hotel_price` | 查某酒店 7/4-7/9 真实房型+价(走 AI_Go_Hotel_MCP 适配) | MCP 直转 |
| `ctrip_health` | 健康检查 — chromium 在不在、产物目录可写 | 本地 |

## 安装 (uv,推荐)

```bash
git clone https://gitee.com/weber-pan/ctrip-mcp.git
cd ctrip-mcp
uv sync
# 装 playwright chromium(容器内首次需要)
uv run playwright install chromium
uv run ctrip-mcp
```

> ⚠️ chromium 较大(~150MB),首次 `playwright install` 需联网。已安装过的容器(本仓库作者容器 `/opt/data` 已有 `~/.cache/ms-playwright/chromium-1223/`)可跳过。

## 配置

无需 token! 抓的是公开 m 端 h5 SPA 接口,无鉴权。

可配环境变量:
- `CTRIP_DATA_DIR` — 抓取产物落盘路径,默认 `/opt/data/ctrip-data/`
- `CTRIP_CHROMIUM` — chromium 路径,默认自动探测
- `CTRIP_TIMEOUT` — 抓取超时秒,默认 60

## 接入 MCP 客户端

### mcphub web UI(本仓库演示实例:[mcp.webertl.top:33399](https://mcp.webertl.top:33399))

**Add Server** → 选 **Stdio**:

| 字段 | 值 |
|---|---|
| Name | `ctrip` |
| Command | `uv` |
| Args | `--directory /opt/data/work/ctrip-mcp run ctrip-mcp` |
| Env (JSON) | `{}` (无需 token) |

`mcphub_smart.json` 等价配置:
```json
{
  "mcpServers": {
    "ctrip": {
      "command": "uv",
      "args": ["--directory", "/opt/data/work/ctrip-mcp", "run", "ctrip-mcp"]
    }
  }
}
```

### Claude Desktop / Cline / Cursor

```json
{
  "mcpServers": {
    "ctrip": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/ctrip-mcp", "run", "ctrip-mcp"]
    }
  }
}
```

## 调用示例

### 在 MCP 客户端里

```python
# 抓携程产品 64158367(上海出发), 等结果返回
result = await mcp.call_tool("ctrip_spa_capture", {
    "product_id": 64158367,
    "depart_city_id": 2
})
# 返回 JSON 字符串, 包含 8 个 graphql/soa 完整 body + DOM 文本

# 解析为结构化报告
summary = await mcp.call_tool("ctrip_get_product", {
    "product_id": 64158367
})
# 返回 4 条线路 / 8 家酒店 / 7 月每日价格 / 点评汇总

# 拿 B/C/D 详细行程
bcd = await mcp.call_tool("ctrip_compare_subproducts", {
    "main_product_id": 64158367,
    "sub_product_ids": [38789419, 73810124, 73810123]
})

# 查酒店真实房价
hotel = await mcp.call_tool("ctrip_get_hotel_price", {
    "hotel_id": 46726,  # 丹绒亚路香格里拉
    "check_in": "2026-07-04",
    "check_out": "2026-07-09",
    "adult_count": 2,
    "room_count": 1
})
```

### 直接命令行 (不通过 MCP)

```bash
export CTRIP_DATA_DIR=/opt/data/ctrip-data
uv --directory /opt/data/ctrip-mcp run python -c "
import asyncio
from ctrip_mcp.capture import spa_capture
result = asyncio.run(spa_capture(product_id=64158367, depart_city_id=2))
print('抓取了', len(result['xhrs']), '个接口')
for tag, path in result['saved'].items():
    print(f'  {tag}: {path}')
"
```

## 关键接口(携程 m 端 h5 SPA 内部 graphql)

| 接口 | 大小 | 拿什么 |
|---|---|---|
| `graphql_ProductInfo_2nd_V3_h5` | ~470KB | 4 条线路 groupCard、8 家酒店、点评汇总、行程 |
| `graphql_VPC_SelectDateProductInfo_h5` | ~330KB | 4 个 sub-productId、7 月全月分价、签证、班期规则 |
| `graphql_ProductInfo_VisaInfo_h5` | ~200KB | 签证详情 |
| `batchPriceCalendar` | ~2KB | 价格日历(优惠明细) |
| `getCommentSummary` | ~6KB | 真实用户点评分(4 条线各 1 条) |
| `getByRelationId` | 几 KB | 关联产品 |
| `getPromotionTag` | 几 KB | 促销标签 |

## 报告字段来源(JSONPath)

| 报告段 | 字段路径 |
|---|---|
| **4 条线路(A/B/C/D)** | `data.productInfo.groupCard.cards[]` → `lineName` / `name` / `priceInfo.minPrice` / `bestTagName` |
| **8 家可自选酒店** | `data.productInfo.imageStyleInfo.hotelInfo.imageHotelList[]` → `hotelId` / `name` |
| **本产品总评** | `data.productInfo.commentInfo.commentAggregation` → `scoreAvg` / `goodRate` / `totalCount` |
| **7 月全月每日最低价** | `data.productInfo.priceCalendar.dailyMinPrices[]` → `hotelDate` / `price` / `originalPriceInfo.originalPrice` |
| **班期价(单条线/单日)** | `data.productInfo.priceCalendar.dailyMinPrices[]` → `productPrices[].productId+price` 4 项 |
| **费用含/不含** | `data.productInfo.FeeInfoList[].ProductClauseList[]` → `ClauseTypeName` + `ClauseSubItemList[].TargetPopulationItemList[].Description` |
| **签证信息** | `data.productInfo.Visa.VisaFeeInfoList[].ClauseItems[].Description` |
| **合同方/品牌** | `data.productInfo.VendorInfo` → `VendorFullName` / `VendorBrand` / `BCNumber` |
| **sub-productId 列表** | `data.TourGroupInfo.TourGroupProductInfo[]` → `ProductId` / `Description` / `SortNumber` |
| **D1-D7 逐日行程(主产品)** | `data.productInfo.TravelIntroductionInfo.TravelIntroductionList[].TravelGroupDesc` |
| **D1-D7 逐日行程(sub-product)** | **graphql 字段不全!** 走 DOM 文本 `D\d\|📍?` 正则抽取 |

## 适用场景

- 用户发携程产品 URL → 真抓 → 完整报告(线路/价格/班期/酒店/点评/优缺点)
- 跨产品横向比价 → 8 个相关产品(从 `MoreRecommendProductList` 拿)
- 4 条线路逐线对比 → 同一产品 4 个 sub-productId 各抓一次
- 7/4 班期价(2 大人)→ `dailyMinPrices[]` `hotelDate=="2026-07-04"` 一次性拿

## Pitfall 日志

- **携程 PC 端反爬严苛**: curl 任何 `soa2/<id>/<method>` 都 403/404
- **m 端壳 HTML 完全无数据**: `__INITIAL_STATE__ = undefined`,`__APP_SETTINGS__` 只有 webpack 路径,真正数据 100% 走 SPA 内部 graphql
- **Playwright `resp.text()` 拿不到 graphql body**: chromium devtools 协议对一次性流式 POST 拿不到 body。**必须用 `add_init_script` hook `window.fetch` + `XMLHttpRequest.send` 把 body 存到 `window.__captured`**
- **on_response handler 注册时机**: 在 `page.goto` **之后**注册会错过初始 burst,导致 0 命中。**先 `page.on("response", cb)`,再 `page.goto`**
- **Hook 注入用 `add_init_script`**: 在所有页面脚本前注入,否则 `window.fetch = ...` 太晚,SPA 内部已缓存原 fetch
- **容器没 chrome 别再 `npx playwright install`**: 用 `~/.cache/ms-playwright/chromium-1223/chrome-linux64/chrome` 现成二进制
- **真抓要滚动到底部**: SPA 用 lazy load,D3 之后的酒店/行程需滚动触发接口
- **sub-product graphql 字段不全**: 主产品返回 `BasicInfo/TravelList/TravelIntroductionInfo/priceCalendar` 全套;sub-product 同样 `ProductInfo_2nd_V3` queryName 拿到的**只有元数据**,**详细 D1-D7 行程藏在 DOM 文本里**
- **4 条线差异在 D4-D5 的"入住哪家酒店"**: A/B/C/D 共享同一 8 家酒店池,D1-D3 D6-D7 完全一致,**真差异 = D4-D5 哪天住哪家**
- **`priceCalendar.scheduleDates` 不一定有 7/4 班期数据**: `scheduleDates[]` 只列部分日期(节假日+采样)。**`dailyMinPrices[]` 才是 7 月全月每日齐全的源**

## 部署架构

```
[用户] --HTTPS--> mcp.webertl.top:33399 (mcphub)
                       |
                       |--stdio--> uv run ctrip-mcp (容器 /opt/data/work/ctrip-mcp)
                       |              |
                       |              v
                       |       Playwright + chromium-1223
                       |              |
                       |              v
                       |       https://m.ctrip.com/webapp/vacations/tour/detail
                       |              |
                       |              v
                       |       内部 graphql/soa 接口
                       |              |
                       |              v
                       |       一手 JSON 落盘 /opt/data/ctrip-data/xhr_*.json
                       |
                       v
                  Claude / Cursor / mcphub 客户端 UI
```

## 与姊妹项目 wendao 版的关系

| | ctrip-mcp(本仓库) | xiecheng-mcp |
|---|---|---|
| 数据源 | 携程 m 端 graphql 接口 | 携程问道 LLM |
| 速度 | 25s/产品 | 10-30s/query |
| 准确度 | ⭐⭐⭐⭐⭐ 真实数据 | ⭐⭐⭐ LLM 复述 |
| 串台风险 | ❌ 无 | ⚠️ 有 |
| 需要 token | ❌ | ✅ WENDAO_API_KEY |
| 需要 chromium | ✅ (~150MB) | ❌ |
| 适用 | 已知产品号,真数据报告 | 自然语言开放问询 |

**建议两个都装,优先用本仓库,wendao 兜底**。

## License

MIT

## 更新日志

### 0.1.0 (2026-06-06)
- 首版发布
- 5 个工具: `ctrip_spa_capture` / `ctrip_get_product` / `ctrip_compare_subproducts` / `ctrip_get_hotel_price` / `ctrip_health`
- 完整真实数据: 4 条线路 / 8 家酒店 / 7 月全月价格 / 点评
- 5 个 pitfalls 文档化
- 1 个 reference 文档(8 家酒店 MCP ID 对照)
