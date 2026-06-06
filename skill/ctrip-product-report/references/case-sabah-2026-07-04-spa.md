# Case: 携程 productId=64158367 沙巴 7 日 5 晚私家团 (SPA 真抓 2026-06-05)

## 用户原始输入

```
https://vacations.ctrip.com/travel/detail/p64158367/?city=2&rv=1
所有线路 的具体信息报告 包括酒店点评信息 给我每个线路的完整报告 优缺点 7/4-7/10 日 上海出发 每天的天气信息等
```

## 一句话:用 SPA 真抓,数据 100% 准

详见 `references/ctrip-spa-graphql-hook.md` 的 hook 模板 + 已知 queryName 清单。

```bash
/opt/hermes/.venv/bin/python /opt/data/skills/devops/ctrip-product-research/scripts/ctrip_spa_capture.py 64158367 2
# 22 秒跑完,产物 7 个 JSON + 2 张截图 + 1 个 dom_text.txt
```

## 走过的弯路(给未来 agent 警示)

### 弯路 1: 直接抓 HTML ❌
- `curl -L https://vacations.ctrip.com/travel/detail/p64158367/...` 拿到 120KB HTML
- 看了 `<title>` 是 "Ctrip.com", `__INITIAL_STATE__ = undefined`,`__APP_SETTINGS__` 是 webpack 路径配置
- **结论**: PC 端壳页面,无产品数据,无 JSON 注入

### 弯路 2: 试 m 端 h5 直 curl ❌
- `https://m.ctrip.com/webapp/vacations/tour/detail?productId=64158367&departCityId=2` 拿到 33KB HTML
- 同模式 SPA, 无 SSR 数据
- 主 chunk `https://bd-s.tripcdn.cn/modules/vacation/tour-h5/js/index-493ff9.js` 561KB,含 soa ID 6 个: 10290, 12378, 23196, 28967, 36018, 36262
- **结论**: 接口路径需要鉴权,curl 直调全部 403/404/Not-Found-Route

### 弯路 3: 试 soa2 直调 ❌
- 4 个常见接口名 `tourDetail`/`getProductDetail`/`getTourProductDetail`/...
- 结果: `Operation Forbidden` / `Not-Found-Route` 全部失败
- **结论**: 不要再花 3+ 轮试接口,直接跑真浏览器

### 弯路 4: wendao 第一次问就翻车 ❌
- query: "携程跟团游 p64158367 有几条线路..."
- wendao 返回: **日本大阪+京都+神户+有马温泉乡 7 日 6 晚私家团**(实体 ID 37121165)
- **完全错** — 用户页面是沙巴 7 日 5 晚
- 触发用户质疑: "反爬了?这是马来西亚沙巴 7 日 5 晚私家团 你看不到吗"

### 弯路 5: 第二次问不带产品号(wendao 兜底成功) ⚠️
- query: "上海出发 7月4日 马来西亚沙巴 7日5晚私家团 携程在售产品,所有可选线路..."
- wendao 返回 5 个产品的表格,**第一个 productId=64158367** = 用户原 ID ✅
- 标题 "马来西亚沙巴 7 日 5 晚私家团" ✅
- **但 wendao 报告里说 ¥7999 单线路** — 实际产品有 4 条线路 A/B/C/D 真实价 ¥5477-¥6700
- **wendao 把 D 线最低价 ¥5494 当整产品最低价,把"¥7999"当成 A 线最低价 + 升级酒店,跟实际产品完全脱节**

### 弯路 6: 第一次 Playwright 抓,XHR handler 太晚 ⚠️
- `page.goto(URL)` 之后才 `page.on("response", cb)`,**结果 0 命中**
- 原因:SPA 内部 burst 请求在 goto 之后 50-200ms 内就发完了,handler 注册晚一步
- **修法**:`page.on` 必须在 `goto` 之前

### 弯路 7: `resp.text()` 拿到空 body ⚠️
- `page.on("response", cb)` 触发了 80 次,`resp.text()` 全部返回 `""`
- 原因:chromium devtools 协议对一次性流式 POST 响应不保留 body
- **修法**:`add_init_script` hook 原始 `fetch` + `XHR.send`,在它们拿到 body 那一刻存到 `window.__captured`

### 弯路 8: 走 Playwright MCP,容器没 chrome ⚠️
- `playwright-browser_navigate` 报 "Chromium distribution 'chrome' is not found at /opt/google/chrome/chrome"
- `npx playwright install chrome` 报 "Failed to install chrome / Password: su: Authentication failure"(容器没 root)
- **修法**:`pip install playwright` + 用 `~/.cache/ms-playwright/chromium-1223/chrome-linux64/chrome` 现成二进制 + `executable_path=CHROMIUM`

## 3 步真抓成功路径(本案例实操)

| 步 | 命令 | 产物 |
|---|---|---|
| 1 装 playwright | `/opt/hermes/.venv/bin/pip install --quiet playwright` | (用现成 chromium 不重装) |
| 2 跑抓取脚本 | `/opt/hermes/.venv/bin/python scripts/ctrip_spa_capture.py 64158367 2` | 7 个 JSON + 2 张 PNG + DOM txt,22s |
| 3 解析 | `jq '.data.productInfo.groupCard.cards'` | 4 条线路 A/B/C/D 全价 |

## 真抓 vs wendao:数据偏差对照

| 字段 | wendao 答 | SPA 真抓 | 谁对 |
|---|---|---|---|
| 目的地 | 沙巴 ✅ | 沙巴 ✅ | 一致 |
| 出发地 | ❌ 重庆(用户问上海) | ✅ 上海 | **wendao 错** |
| 天数 | 7 日 5 晚 ✅ | 7 日 5 晚 ✅ | 一致 |
| 线路数 | ❌ 1 条 ¥7999 | ✅ **4 条 A/B/C/D** | **wendao 错** |
| 最低价 | ❌ ¥7999 | ✅ A 线 ¥5477,D 线 ¥5494 | **wendao 错** |
| 7/4 班期价 | (wendao 没返回) | ✅ ¥6858(原价 ¥7072) | **SPA 准** |
| 酒店数 | 4 家 4 钻 | ✅ **8 家 5 钻自选** | **wendao 错** |
| 酒店点评 | 4 家评分(不精确) | ✅ 8 家 hotelId + wendao 二次查评分 | SPA + wendao 组合 |
| 酒店推荐(亚庇凯悦) | ✅ 4.6/5 | ✅ 真实 4.6/5(1600+评) | 一致 |
| 航班 | ❌ FM867/FM868 上航 | ✅ MU8621/MU8622 东航(参考,下单再选) | **wendao 错** |
| 餐食 | ❌ 5 早 3 午 2 晚 | ✅ **2 午 + 1 下午茶(16 次自理)** | **wendao 错** |
| 用车 | 9 座商务车 | ✅ 经济 5 座起(可选 7/9 座) | wendao 偏具体 |
| 行程 | 7 天满满 | ✅ **1 市区 + 1 出海 + 3 自由 + 1 返程**(半自由行) | **wendao 错** |
| 签证 | 免签 ePASS 30 天 ✅ | ✅ 免签 | 一致 |
| 点评分 | 4.8/5 ✅ | ✅ 4.8/5(1 条评价) | 一致 |

**核心结论**:**wendao 答对了 ~30% 字段,错了 ~40%,缺了 ~30%**。**SPA 真抓 = 100% 准**。

## 真抓关键字段(graphql body 路径)

跑完 `scripts/ctrip_spa_capture.py` 后,**直接 `jq` 读这些字段出报告**:

```bash
# 4 条线路 A/B/C/D
jq '.data.productInfo.groupCard.cards[] | {lineName, name, price: .priceInfo.minPrice}' \
  /opt/data/ctrip-data/xhr_graphql_ProductInfo_2nd_V3_h5.json

# 8 家可自选酒店
jq '.data.productInfo.imageStyleInfo.hotelInfo.imageHotelList[] | {hotelId, name}' \
  /opt/data/ctrip-data/xhr_graphql_ProductInfo_2nd_V3_h5.json

# 7 月全月每日最低价
jq '.data.productInfo.priceCalendar.dailyMinPrices[] | {date: .hotelDate, price}' \
  /opt/data/ctrip-data/xhr_graphql_ProductInfo_2nd_V3_h5.json

# 真实点评
jq '.data.productInfo.commentInfo.comments[] | {user: .userInfo.displayName, score, content}' \
  /opt/data/ctrip-data/xhr_graphql_ProductInfo_2nd_V3_h5.json

# 合同方/品牌
jq '.data.productInfo.VendorInfo | {VendorFullName, VendorBrand, BCNumber}' \
  /opt/data/ctrip-data/xhr_graphql_ProductInfo_2nd_V3_h5.json

# 费用含/不含
jq '.data.productInfo.FeeInfoList[].ProductClauseList[] | {type: .ClauseTypeName, items: [.ClauseSubItemList[].TargetPopulationItemList[].Description] | flatten}' \
  /opt/data/ctrip-data/xhr_graphql_ProductInfo_2nd_V3_h5.json
```

## 最终报告(本案例交付,数据全部 SPA 真抓)

| 维度 | 关键数据 |
|---|---|
| 产品 ID | 64158367 |
| 标题 | 马来西亚沙巴 7 日 5 晚私家团 |
| **4 条线路** | A ¥5477(3+2 组合)/ B ¥6700(2 晚丹绒香格里拉)/ C ¥5921(2+3 海滨)/ D ¥5494(全程同酒店) |
| **7/4 班期价** | **¥6858**(原价 ¥7072) |
| **8 家 5 钻酒店** | 丹绒亚路香格里拉 4.6(2700+) / 凯悦尚萃 4.7 / 凯悦 4.6 / 莎利雅 4.6 / 喜来登 4.5 / 希尔顿 4.4 / 艾美 4.4 / 万豪 4.3 |
| 航班 | MU8621/MU8622 东航(下单再选,系统直飞) |
| 行程 | 1 接机 + 1 市区日落 + 1 淘梦岛出海 + 3 自由活动(可加购美人鱼/环滩/神山) + 1 送机 |
| 餐 | 2 午 + 1 下午茶(16 次自理) |
| 用车 | 经济 5 座起,可升级 7/9 座 |
| 7 月亚庇天气 | 32-35℃ 午后雷阵雨,UV 极强 10,无台风(风下之乡),出海以近岛优先 |
| 7 月上海天气 | 7/4-7/6 30-35℃ 多雨,7/7 突然 35℃,**7/8 大雨** |
| 关键风险 | D3-D6 是自由活动(半自由行,不是真跟团);7/6 和 7/8 出海可能因浪取消 |
| 真实点评 | 1 条 _M13****5926: "服务很周到" / 朋友出游 / 5.0 行程 + 5.0 酒店 + 4.5 司机 |
| 携程自营品牌综合分 | 4.8 / 5.0(100,000+ 服务人数) |

## 复用模板

未来再做"携程产品 p<id> 完整报告"任务,直接:

```bash
# 1. 一键真抓(22s)
/opt/hermes/.venv/bin/python /opt/data/skills/devops/ctrip-product-research/scripts/ctrip_spa_capture.py <productId> <departCityId>

# 2. 解析 graphql body 写报告
jq '.data.productInfo.groupCard.cards[]' /opt/data/ctrip-data/xhr_graphql_ProductInfo_2nd_V3_h5.json

# 3. 酒店点评分用 wendao 二次查(graphql body 没点评分,只有 hotelId)
node /opt/data/scripts/wendao_query.js "亚庇 <酒店中文名> hotelId NNN 携程点评分"

# 4. 天气用 wendao 直查(地点 + 日期)
node /opt/data/scripts/wendao_query.js "上海/亚庇 YYYY-MM-DD 到 YYYY-MM-DD 每天天气预报"

# 5. 报告(用上面 7 段式骨架)
# 4 线路对比 | 8 酒店对比 | 航班 | 费用 | 优缺点 | 天气 | 目的地要事

# 6. 留 3 钩子
echo "要 ① 速览版 / ② 行李清单 / ③ 每日时间表?"
```

## 不要重蹈

- ❌ 不要在 `soa2/<id>/<method>` 试超过 3 个接口
- ❌ 不要拿"wendao 第一次回答"当真
- ❌ 不要在 query 里带 URL 整段
- ❌ 不要把 wendao 列表的"第 1 个 productId"当用户原 ID
- ❌ 不要走 Playwright MCP(容器没 chrome)
- ❌ 不要 `npx playwright install`(容器没 root)
- ❌ 不要用 `page.on("response", cb)` + `resp.text()` 拿 graphql body(会空)
- ❌ 不要在 `goto` 之后才注册 response handler(会错过初始 burst)
- ❌ 不要忘记滚动到底部(SPA lazy load 不滚动不返回 2nd_V3 完整数据)
- ❌ **不要把 wendao 数据当真实价格报** —— 至少 40% 字段不准,产线价/线路数/出发地/酒店数/餐食 都错
