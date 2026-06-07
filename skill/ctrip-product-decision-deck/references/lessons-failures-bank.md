# 产品 PPT 翻车案例库 (Lessons Bank)

> 这是 ctrip-product-decision-deck skill 下的失败案例 / 教训集中地. 当 agent 拿不到"用户确认数据真伪"和"图都放哪了"两件事时, 大概率复现以下踩坑. **新 session 开始前必读本文件**, 然后跑 ppt-master SKILL.md 末尾的「产品 PPT 必走 7 项检查」.

## 案例 1: p69852382 v1 → v3 翻车全过程 (2026-06-07, 1.5 小时)

### 背景
- 产品: 巴厘岛 7 日 5 晚私家团, productId=69852382, 4 条 subProductId (A/B/C/D)
- 出差双人, 7/4-7/10 上海出发
- 用户: xsct-bench 作者, 对"数据真实度 + 配色 + 详细度"敏感, 偏好中文

### v1 翻车 (28 页, 用户回: "你是不是只给了 A 线?" + "官方的图片也没插入")
**踩的坑**:
1. ❌ 只抓主产品 ProductInfo (1 个 subProductId 69852382 = A 线), 没跑 `ctrip_compare_subproducts` 拿 B/C/D 行程/酒店
2. ❌ 4 条线数据只在 P07 价格日历 4 行带过, P03 02 行 + P22 预算 + P10 KPI 全是 A 线主体
3. ❌ 0 张官方图, 0 张酒店实拍, 0 张景点图
4. ❌ 用户对"给谁看"+"站在旅客角度"+"分析到位"没感知 (文字空话)

### v2 修一半 (25 页, 用户没确认就推进)
**改的**:
1. ✅ P06 新增"4 线对比表" (7 个日期 × 4 条线单人+双人价)
2. ✅ P10 KPI 改 4 卡显示 A/B/C/D
3. ✅ P03 02 行加 4 线比价文字
4. ❌ 仍 0 张图 — 用户没明说但暗含"应该有图"

### v3 全修 (28 页, 1.22 MB, 13 张图嵌入)
**改的**:
1. ✅ 走 `/opt/data/ctrip-data/xhr_ProductInfo_2nd_V3_h5_<productId>.json` 抽 4 类图 URL:
   - `data.productInfo.imageStyleInfo.poiInfo.ImagePoiList[].imgUrl` → 10 张 POI
   - `data.productInfo.imageStyleInfo.hotelInfo.imageHotelList[].imageList[].imgUrl` → 1 家 3-5 张
   - `data.productInfo.commentInfo.comments[].userInfo.avatarUrl` → 2-5 张
   - `data.productInfo.productExtend.MoreRecommendProductList[].ImageUrl` → 4-8 张 banner (次要)
2. ✅ curl 下载 15 张 (10 POI + 3 hotel + 2 avatar) + PIL 缩到 800x600 q82 → 13 张 / 1 MB
3. ✅ 建 P26 (4 线代表图) + P27 (酒店精选 3 张) + P28 (行程 9 景点 3x3)
4. ✅ SVG base64 嵌图 → svg_to_pptx 自动解压到 ppt/media/image_*.jpg

### 关键 mcp 工具 (4 个)
- `携程官网-ctrip_spa_capture(productId)` → 8 个 xhr JSON + 截图
- `携程官网-ctrip_get_product(productId)` → 解析 ProductInfo 拿酒店/点评/价格日历
- `携程官网-ctrip_compare_subproducts(main, [sub1,sub2,sub3,sub4])` → 1 次拿 4 线差异
- `AI_Go_Hotel_MCP-getHotelDetail(hotelId, dateParam)` → 走酒店系统查实时房型+价

### 教训 (新 session 第一件事问自己)
1. **多线产品** = 必跑 `ctrip_compare_subproducts` 拿 4 subProductId 全程差异, **没跑 = 用户问"只给了 A 线"概率 100%**
2. **任何产品 PPT** = 必抓 4 类图 + 必建 P26-P28 3 张图集页, **漏了 = 用户回"官方的图片也没插入"**
3. **P07 价格日历 4 行** = 表层, 真正要单建 P06 4 线对比表 + P10 KPI 4 卡
4. **图嵌入姿势** = SVG `<image href="data:image/jpeg;base64,XXX" />` → svg_to_pptx 自动解压到 ppt/media/, **不要走 base64 后再 base64 (会爆)**

---

## 案例 2: 多 MCP 串台 — 7/8 ¥5,886 vs 7/7 ¥5,716 数据真实度 (2026-06-07)

### 背景
- D 线 (subProductId 63621261) 价格日历里 7/4-7/10 **只 7/7, 7/8, 7/11 三天有班期**
- 7/7 ¥5,716 vs 7/8 ¥5,716, 看似一样, 实际 7/8 库存 5 位 7/7 库存 10 位
- A 线 7/4 ¥7,543 vs A 线 7/8 ¥5,886 = 同一产品跨日期差 ¥1,657

### 坑
- 用户问"5,886 是真的还是截图?" → 答 e2e price_calendar.by_date['2026-07-08'][0].price, 截图 vs 抓取价有出入
- 解释: 截图是 7 月起价, 抓取价是 7/8 班期价, **不要把"起价"和"班期价"混着说**

### 守则
- 报告里标"携程 e2e 真抓 8 接口" vs "用户截图", 让用户能核
- 起价 ≠ 班期价 ≠ 库存价 (3 概念, 必分开列)

---

## 案例 3: SVG → PPTX 中文 & 转义坑 (2026-06-07 v4/v5 复用)

### 坑 1: `&` 未转义
- `佩妮达&蓝梦` 直接写 SVG → svg_to_pptx 报 `P03 line 30 invalid token`
- 修: `&amp;`, 批量正则修全 28 张: `s/&/&amp;/g` (除已转义)

### 坑 2: Pillow 没装 + convert 命令缺失
- `convert` (imagemagick) 不在 worker 容器 PATH, 改用 PIL:
  ```python
  from PIL import Image
  im = Image.open(src); im.thumbnail((800, 600), Image.LANCZOS)
  im.save(dst, 'JPEG', quality=82, optimize=True)
  ```

### 坑 3: 复用 v4 SVG 时 P14/P15/P16 文件名撞车
- v4 = 泗水+布罗莫多岛 (P14_bromo/P15_ijen/P16_penida)
- v5 = 巴厘岛单岛 (P14_d2d3_bromo/P15_d4_ijen/P16_d5d6_lovina_penida)
- cp v4 → workspace 时残留 v4 文件, 需要手动 `os.remove` 残留 14_bromo.svg / 15_ijen.svg / 16_penida.svg

### 坑 4: svg_to_pptx 跳过 >0 报错
- 必须 0 skipped, 否则 PNG 看图正常但 PPTX 缺元素
- `Converted 9 elements, skipped 0` ← 这个 0 是关键

---

## 案例 4: 用户的元偏好 (必嵌 skill 不嵌 memory)

### 用户原话 (2026-06-07)
> "你都没写进 skill 里面吗, 让智能体不会忘记 这种对比的策略啊"

### 翻译成可执行守则
- ❌ **错的做法**: 把"4 线对比必抓" + "图必塞" 写进 MEMORY.md (跨 session 知道, 但新 session 不主动触发)
- ✅ **对的**: 写进 ppt-master SKILL.md 末尾「产品 PPT 必走 7 项检查」+ ctrip-product-decision-deck SKILL.md 10.7 节 + 触发描述里加"对比 / 图"关键词
- **新 session** 看到产品 URL → 自动 load 这 2 个 skill → 自动跑 7 项检查 → 不再问用户"要不要做 4 线对比"

### 同样适用的其他场景 (用户偏好)
- 配色丑 → 写进 editorial-magazine-design 触发词 + popular-web-designs 推荐
- 详细不到位 → 写进 ctrip-product-decision-deck 触发词加"详细"+"分析到位"
- 给谁看 → 写进 audience_branching.svg 模板 + ctrip-product-decision-deck §3 客群分流

---

## 案例 5: 子产品 4 线 subProductId 推断 (mcphub 没有 ID 列表, 靠 price_calendar 反推)

### 背景
- 用户给 1 个 productId (如 69852382), 看不到 subProductId 列表
- 4 条线名字只在"线路班期"截图里出现

### 推断法
- 抓主产品 ProductInfo, 看 `by_date['2026-07-08']` 有几条 lineName
- 每条 lineName 对应一个 subProductId
- 反查: 同 lineName 在 `by_date['2026-07-09']` 也出现, productId 字段就是 subProductId

### 实战: p69852382 4 线 subProductId 映射
| 线 | subProductId | lineName | 7/4 单人价 |
|---|---|---|---|
| A | 69852382 | 高性价5钻｜双岛出海+可追海豚 | ¥7,543 |
| B | 69960194 | 小众秘境｜4晚海边别墅+追海豚 | ¥9,184 |
| C | 71330231 | 2晚阿雅娜+设计别墅｜专属包团 | ¥11,793 |
| D | 63621261 | 全国联运+双岛出海｜A线同款 | — (7/4 不开放) |

### 守则
- 4 个 subProductId 抓完后, **必建 P06 4 线对比表** (不是 P07 价格日历 4 行, 是新 P06 一页)
- **D 限班期** = 必标红 "7/4-7/10 仅 X X X 班期" 警示
