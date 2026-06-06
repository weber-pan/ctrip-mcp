---
name: ctrip-spa-capture
description: 携程 m 端 h5 SPA 真抓技术层 — 拿产品号(productId)后,用 Playwright + chromium + fetch/XHR hook 抓 m.ctrip.com 内部 graphql/soa 一手 JSON, 产物落 xhr_*.json + DOM + 截图。**自动双跑** `ProductInfo_2nd_V3_h5` + `VPC_SelectDateProductInfo_h5`, 落盘完整价格日历 CSV + 4 类图片(15+ 张) + 11 段"被遗忘字段"。触发: 用户要"真抓" / 提到 "p<productId>" / 问 "数据是真实的吗" / 问 "价格日历" / 问 "图片下载" / 问 "city=2 是什么城市"。

# ctrip-spa-capture

Playwright 真抓携程 m 端 h5 SPA — 0 token, ~15s/产品。

## 1. 用法

```bash
# 抓取(必须先)
python3 scripts/ctrip_spa_capture.py <productId> <cityId>
# e.g.
python3 scripts/ctrip_spa_capture.py 69762187 2      # 上海
python3 scripts/ctrip_spa_capture.py 69762187 1      # 北京
python3 scripts/ctrip_spa_capture.py 69762187 32     # 广州
python3 scripts/ctrip_spa_capture.py 69762187 1244   # 重庆
# 输出: /opt/data/ctrip-data/xhr_*.json + dom_text.txt + *.png

# 提取更多字段(可选, 抓完后)
python3 scripts/extract_more.py <productId>
# 输出:
#   price_calendar_<id>.csv  (207 天)
#   img_<id>/  (15+ 张图 + manifest.json)
#   stdout 11 段提取
```

## 2. city 规律(国内机场城市 ID 字典)

`url?city=2` 不是地区码, 是**携程内部"出发城市 ID"**:

| ID | 城市 | ID | 城市 |
|---|---|---|---|
| 1 | 北京 | 17 | 杭州 |
| 2 | **上海** | 28 | 成都 |
| 3 | 天津 | 30 | 深圳 |
| 5 | 哈尔滨 | 32 | 广州 |
| 12 | 南京 | 1244 | 重庆 |

**68 个城市**(携程支持的所有国内出发地), 完整列表在抓取后的 `DepartureCityPriceList[]` 里。

**任意城市 3 种方式**:
1. URL 改 `city=XX`(数字)
2. 脚本加 `--city-id` 参数
3. 从 2nd_V3 `DepartureCityPriceList[]` 找 ID

## 3. 11 段"被遗忘字段"(extract_more.py 输出)

| 段 | 数据源 | 例子 (p69762187) |
|---|---|---|
| 1 价格日历 | VPC.dailyMinPrices[] | 207 天 6/8-12/31, CSV |
| 2 图片 | DescriptionInfo+POI+PM+brandTag | 15 张 (3 banner + 7 POI + 1 PM + 4 brand) |
| 3 7 段摘要 | cardItems[] | 行=飞机/住=5晚4钻/团=不拼/游=16/餐=6早1午 |
| 4 行程结构 | SegmentInfo.Segments[] | 10 段(上海→泗水→Kanigaran→Licin→巴厘岛→上海) |
| 5 可选酒店 | imageHotelList[] | 9 家(带 hotelId, 可调 hotelMCP) |
| 6 目的地 | Destinations[] | 13 项(1 国 2 省 10 城) |
| 7 出发城市价 | DepartureCityPriceList[] | 68 城, 上海 ¥7557 / 深圳 ¥6345 |
| 8 销量流量 | OrderPersonCount+VacationPersons | 328 销 / 8636 月访问 |
| 9 点评 | getCommentSummary | 评分/数量/前 3 条 |
| 10 特殊费用 | FeeInfoList → TargetPopulationItemList | 巴厘岛 15 万印尼盾旅游税 + 落地签 35 美金 |
| 11 竞品 | MoreRecommendProductList[] | 8 个, 拼小团最便宜 ¥6412 |

## 4. 关键技术

- **0 token**: m 端 graphql 接口无鉴权
- **fetch + XHR 双 hook**: SPA 老代码可能用 XHR
- **add_init_script**: 在页面所有脚本前注入
- **graphql 端点统一**: `?queryName=XXX` 是 method 名, 不是 URL 末尾
- **双接口合并**: 2nd_V3(34 字段) + VPC(16 字段) ≈ 50 字段, 互相补全
- **chromium 自动探测**: `~/.cache/ms-playwright/chromium-1223/chrome-linux64/chrome`
- **子产品命名**: 文件名加 `_pid` 避免多产品覆盖(沙巴数据用此规则)

## 5. Pitfall 日志(踩过的坑)

1. **DOM 文本 != 结构化数据** — 行程 D1-D7 用 DOM 拿不准, 改用 `SegmentInfo`
2. **Title 在 2nd_V3 缺失** — 必须查 `BasicInfo.Title`(VPC 才有)
3. **DescriptionInfo.Introduction 是 HTML** — 不是文本, 要 `re.findall('<img')`
4. **POI 字段是 `imgUrl` 不是 `imageList`** — 之前 `p.get('poiName')` 写错
5. **productPrices[].productId** — 同日期下有多个子产品价(VPC 才有)
6. **`/Date(ms+0800)/` 格式** — 用 `_parse_net_date` 转 ISO 字符串
7. **None 不是抓取 bug** — SPA 后端只发非空字段, 缺字段 = 真没填
8. **feeInfoList.Description 字段不存在** — 真实数据在 `TargetPopulationItemList[].Description`
9. **cardItems vs TravelSummaryModuleList** — 不同产品用不同模板, 适配两套

## 6. 下游消费者

- `ctrip-product-report` (umbrella 子 skill) — 用本层 JSON 生成 11 段报告
- `ctrip-mcp` (gitee) — 封装本层为 MCP 工具, 跨客户端调用

## 7. 测试样本

`/opt/data/ctrip-data/` 留有 3 份真实样本:
- `xhr_ProductInfo_2nd_V3_h5_64158367.json` — 沙巴 4 线路 (¥5763 起, 沙巴)
- `xhr_graphql_ProductInfo_2nd_V3_h5.json.p42461732` — 印尼 1 线路 (¥4812, 泗水出发, 14 模块模板)
- `xhr_graphql_ProductInfo_2nd_V3_h5.json` — 印尼 1 线路 (¥7557, 上海出发, 7 段模板)
- `price_calendar_69762187.csv` — 207 天价格日历
- `img_42461732/`, `img_69762187/` — 15 张/份图片
