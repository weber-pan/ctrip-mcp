# Case: 携程 productId=64158367 沙巴 7 日 5 晚私家团(2026-06-05 实测)

## 用户原始输入

```
https://vacations.ctrip.com/travel/detail/p64158367/?city=2&rv=1
所有线路 的具体信息报告 包括酒店点评信息 给我每个线路的完整报告 优缺点 7/4-7/10 日 上海出发 每天的天气信息等
```

city=2 = 上海出发, 7/4-7/10 = 6 晚 7 日(wendao 给出 5 晚 7 日 = Day1 飞抵夜算 Day1,Day7 凌晨返程, 实际 5 晚酒店)

## 走过的弯路(给未来 agent 警示)

### 弯路 1: 直接抓 HTML
- `curl -L https://vacations.ctrip.com/travel/detail/p64158367/...` 拿到 120KB HTML
- 看了 `<title>` 是 "Ctrip.com", `__INITIAL_STATE__ = undefined`,`__APP_SETTINGS__` 是 webpack 路径配置
- **结论**: 壳页面,无产品数据,无 JSON 注入

### 弯路 2: 试 m 端 h5
- `https://m.ctrip.com/webapp/vacations/tour/detail?productId=64158367&departCityId=2` 拿到 33KB HTML
- 同模式 SPA, 无 SSR 数据
- 主 chunk `https://bd-s.tripcdn.cn/modules/vacation/tour-h5/js/index-493ff9.js` 561KB,含 soa ID 6 个: 10290, 12378, 23196, 28967, 36018, 36262
- **结论**: 接口路径需要鉴权,curl 直调全部 403/404/Not-Found-Route

### 弯路 3: 试 soa2 直调
- 4 个常见接口名 `tourDetail`/`getProductDetail`/`getTourProductDetail`/...
- 结果: `Operation Forbidden` / `Not-Found-Route` 全部失败
- **结论**: 不要再花 3+ 轮试接口,直接 wendao

### 弯路 4: wendao 第一次问就翻车
- query: "携程跟团游 p64158367 有几条线路..."
- wendao 返回: **日本大阪+京都+神户+有马温泉乡 7 日 6 晚私家团**(实体 ID 37121165)
- **完全错** — 用户页面是沙巴 7 日 5 晚
- 触发用户质疑: "反爬了?这是马来西亚沙巴 7 日 5 晚私家团 你看不到吗"

### 弯路 5: 第二次问不带产品号
- query: "上海出发 7月4日 马来西亚沙巴 7日5晚私家团 携程在售产品,所有可选线路..."
- wendao 返回 5 个产品的表格,**第一个 productId=64158367** = 用户原 ID ✅
- 标题 "马来西亚沙巴 7 日 5 晚私家团" ✅, "重庆直飞" (注意:wendao 这次说重庆,但用户给的是 city=2 上海,wendao 在出发地上也有出入)
- 验证产品号对了,后面继续

### 弯路 6: 短 query 串台
- "携程产品 71068823 是不是马来西亚沙巴 7 日 5 晚私家团" → wendao 回"重庆直飞亚庇,6721 元起"
- 71068823 是 wendao 列出的另一个产品,不是用户问的
- **但回答本身数据完整可信**:包含逐日行程+价格+优缺点
- 用法: 把列表里每个 productId 都问一遍,收集所有线路数据,再交给用户挑

## 5 步交叉验证(本案例实操)

| 步 | query | 关键输出 |
|---|---|---|
| 1 | "携程跟团游 p64158367 有几条线路..." | ❌ 错(日本大阪) |
| 2 | "上海出发 7月4日 马来西亚沙巴 7日5晚私家团..." | ✅ 5 产品列表,第 1 个 = 64158367 |
| 3 | 比对 | destinations: 沙巴 ✅, 出发地: city=2=上海, wendao 说重庆, 存疑, 报告中标"wendao 称重庆直飞" |
| 4 | 重问 with "上海" | wendao route_full 答:"上海浦东机场集合, 7/4 20:00-00:30+1 FM867 直飞亚庇" → 修正出发地为上海 ✅ |
| 5 | 报告标注 | "数据来源: 携程问道(wendao-skill),不是直接抓的; 携程 PC 端反爬严苛" |

## 最终报告(本案例交付)

| 维度 | 关键数据 |
|---|---|
| 产品 ID | 64158367 |
| 标题 | 马来西亚沙巴 7 日 5 晚私家团(行程 N 选 1, 实际只查到 1 条线路) |
| 价格 | 成人 ¥7999, 儿童 ¥6500, 单房差 ¥1200 |
| 酒店 | 5 晚同一家 4 钻, 备选: Hyatt Regency Kinabalu(4.6) / Horizon(4.5) / Promenade(4.4) / Grandis(4.3) |
| 航班 | 去 FM867 7/4 20:00-00:30+1, 返 FM868 7/10 01:30-05:55, 各 23kg 托运 |
| 行程亮点 | 1 市区 + 1 红树林(KAWA 萤火虫) + 1 出海(东姑阿都拉曼) + 1 美人鱼岛 + 1 神山 + 1 自由 |
| 餐 | 含 5 早 3 午 2 晚 |
| 7 月亚庇天气 | 32-33℃ 午后雷阵雨, UV 11+ 极强, 无台风(风下之乡), 出海以近岛优先 |
| 7 月上海天气 | 7/4-7/6 35-38℃ 高温, 7/8 大雨(影响返程或行中) |
| 关键风险 | 返程红眼 + 凌晨抵沪; 美人鱼岛易因风浪改岛; 神山 1 项自费 + 温泉 50 马币 |

## 复用模板

未来再做"携程产品 p<id> 完整报告"任务,直接:

```bash
# 1. 5 步交叉验证
for q in "step1" "step2" "step3" "step4" "step5"; do
    node /opt/data/scripts/wendao_query.js "$q" > /opt/data/ctrip-data/$q.md
done

# 2. 报告(用上面 7 段式骨架)
# Day1-DayN 行程 | 酒店对比 | 航班 | 费用 | 优缺点 | 天气 | 目的地要事

# 3. 留 3 钩子
echo "要 ① 速览版 / ② 行李清单 / ③ 每日时间表?"
```

## 不要重蹈

- ❌ 不要在 `soa2/<id>/<method>` 试超过 3 个接口
- ❌ 不要拿"wendao 第一次回答"当真
- ❌ 不要在 query 里带 URL 整段
- ❌ 不要把 wendao 列表的"第 1 个 productId"当用户原 ID(虽然这次正好对上,纯属运气)
- ❌ 不要遗漏"wendao LLM 串台可能性"警告
