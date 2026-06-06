---
name: ctrip-product-report
description: 携程跟团游/私家团产品**报告生成工作流** — 拿到原始 JSON(由 ctrip-spa-capture 抓 或 ctrip-mcp 给)后,**拼装"7 段行程 + 酒店点评分 + 费用明细 + 优缺点 + 同期天气 + 11 段补漏"完整报告**。触发: 用户发携程产品 URL、提到 p<productId>、问"几条线路""每天行程""点评分""优缺点""完整价格日历""城市字典""图片下载"。**必须先加载 [ctrip-spa-capture](../ctrip-spa-capture/SKILL.md) 拿到 JSON**。

# 携程产品报告 — 拼装模板

## 报告结构(11 段 — 升级版)

| 段 | 来源字段 | 例子 (p69762187) |
|---|---|---|
| 1️⃣ **基础元数据** | `BasicInfo` (VPC) | 上海→泗水, 7 日 6 晚, 起 ¥7557 |
| 2️⃣ **销量/流量** | `OrderPersonCount` + `VacationPersons` | 328 销 / 月 8636 访问 |
| 3️⃣ **7 段摘要** | `cardItems[]` 或 `TravelSummaryModuleList` | 行=飞机/住=5晚4钻/团=不拼/游=16/餐=6早1午 |
| 4️⃣ **行程结构** | `SegmentInfo.Segments[]` | 10 段 (上海→泗水→Kanigaran→Licin→巴厘岛→上海) |
| 5️⃣ **可选酒店** | `imageHotelList[]` | 9 家, 带 hotelId |
| 6️⃣ **景点 POI** | `ImagePoiList[]` | 8 个, 带 poiId |
| 7️⃣ **费用含/不含** | `FeeInfoList[].ProductClauseList[].ClauseSubItemList[].TargetPopulationItemList[]` | 9 类 + 巴厘岛旅游税 |
| 8️⃣ **价格日历** | `priceCalendar.dailyMinPrices[]` (CSV) | 207 天 |
| 9️⃣ **同价位竞品** | `MoreRecommendProductList[]` | 8 个 |
| 🔟 **天气 + 实用信息** | 高德/wendao + 签证 + 班期 | 7/4 ¥8947 |
| 1️⃣1️⃣ **优缺点 + 报告评分** | 综合分析 | ⭐⭐⭐⭐ |

## 工作流

### 输入

1. **JSON**: `/opt/data/ctrip-data/xhr_*.json` (ctrip-spa-capture 抓的)
2. **价格日历**: `/opt/data/ctrip-data/price_calendar_<pid>.csv`
3. **图片**: `/opt/data/ctrip-data/img_<pid>/`
4. **城市**: 用户 URL `?city=XX` (默认 2=上海)

### 处理步骤

1. **加载数据** (2nd_V3 + VPC 双接口, 合并使用)
2. **7 段摘要** (cardItems 优先, TravelSummaryModuleList 兜底)
3. **行程结构** (10 段 SegmentInfo, 不靠 DOM)
4. **酒店列表** (imageHotelList 9 家)
5. **费用拆解** (TargetPopulationItemList 成人/儿童)
6. **价格日历区间查询** (用户问"7/4-7/10"或"8 月"用 CSV)
7. **同价位竞品比价** (MoreRecommendProductList)
8. **天气** (高德 ≤ 4 天 + wendao 7/4 + 风险提示)
9. **签证** (Visa.Detail, 特别关注落地签金额)
10. **图片插入** (DescriptionInfo/POI/PM/brandTag 4 类)
11. **优缺点** (基于 11 段综合)

### 输出格式 (markdown)

```markdown
# [产品名] 完整报告

## 1️⃣ 基础元数据
| 字段 | 值 | 数据源 |
|---|---|---|
| 产品 | ... | BasicInfo.Title (VPC) |
| 起价 | ... | PriceInfo.MinPrice (2nd_V3) |
| 销量 | ... | OrderPersonCount (VPC) |
| 行程 | ... | TravelDays/Nights (VPC) |

## 2️⃣ 销量/流量
...

## 3️⃣ 7 段摘要 (cardItems)
| 段 | 内容 |
|---|---|
| 行 | 飞机往返 |
| 住 | 含 5 晚 4 钻 |
...

## 4️⃣ 行程结构
| 段 | 起→止 | 交通 | 住宿 |
|---|---|---|---|
| 1 | 上海→泗水 | ✈️ | - |
| 2 | 泗水 | 🚐 | 1 晚 |
...

## 5️⃣ 可选酒店 (9 家)
| 酒店 | 星级 | 评分 | 排行 | hotelId |
|---|---|---|---|---|

## 6️⃣ 景点 (8 个)
| 景点 | poiId | img |
|---|---|---|

## 7️⃣ 费用含/不含
### 费用包含
| 类别 | 成人 | 儿童 |
|---|---|---|
### 自理费用
...

## 8️⃣ 价格日历
(月度统计表 + 区间查询结果)

## 9️⃣ 同价位竞品
| 竞品 | 价格 | 区别 |
|---|---|---|

## 🔟 天气 + 实用信息
| 日期 | 城市 | 天气 | 数据源 |
|---|---|---|---|

## 1️⃣1️⃣ 优缺点
- ⭐⭐⭐⭐ ...
- 优点: ...
- 缺点: ...
```

## 关键字段对照

| 字段 | 2nd_V3 | VPC | 备注 |
|---|---|---|---|
| Title/完整产品名 | ❌ 缺失 | ✅ BasicInfo | 必查 VPC |
| MinPrice | ✅ | ✅ | 一致 |
| TravelList/行程 | ❌ 空 | ✅ SegmentInfo 10 段 | 行程必查 VPC |
| OrderPersonCount/销量 | ❌ | ✅ BasicInfo | 销量必查 VPC |
| DepartureCityPriceList/多城价 | ✅ 68 城 | ❌ | 多城价查 2nd_V3 |
| cardItems/7 段摘要 | ✅ | ❌ | 摘要查 2nd_V3 |
| TravelSummaryModuleList/14 模块 | ✅ (部分产品) | ❌ | 老模板 |
| DescriptionInfo/HTML 介绍 | ✅ | ❌ | 介绍查 2nd_V3 |
| imageHotelList/9 酒店 | ✅ | ❌ | 酒店查 2nd_V3 |
| Visa/签证 | ✅ | ❌ | 签证查 2nd_V3 |
| getCommentSummary/点评 | 独立接口 | - | 必查 getCommentSummary |
| compositeCoupon/优惠券 | ✅ (部分) | ❌ | 促销查 2nd_V3 |

## Pitfall 日志

1. **Title 在 2nd_V3 缺失** → 改查 `BasicInfo.Title` (VPC)
2. **Name/Description 为空** → 不是 bug, 是新 SPA 不发, 用 `TravelOverviewInfo` 模块表兜底
3. **feeInfoList.Description 字段不存在** → 真实数据在 `TargetPopulationItemList[]`
4. **cardItems vs TravelSummaryModuleList** → 不同产品用不同前端模板, 两套都要适配
5. **8/8 等日期价 ¥0** → 库存 0 或关闭班期, 过滤掉
6. **行程 D1-D7 拿不准** → 优先用 `SegmentInfo` (10 段), DOM 兜底
7. **天安门级坑** `city=2` 是国内出发城市 ID, 2=上海, 完整字典见 `ctrip-spa-capture` SKILL.md 第 2 节

## 输出样本

- `/opt/data/ctrip-data/REPORT_p69762187_full.md` (8.2KB, 11 段全)
- `/opt/data/ctrip-data/REPORT_p42461732_mined.md` (8.4KB, 5 段 + 6 段补漏)
- `/opt/data/ctrip-data/REPORT_debug_none_img_weather_hotel.md` (7.6KB, 排查报告)
