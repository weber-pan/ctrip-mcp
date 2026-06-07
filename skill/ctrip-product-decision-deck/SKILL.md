---
name: ctrip-product-decision-deck
description: 携程产品决策手册 PPT 工作流 — 用户给产品 URL → 8 字段确认 → 多 MCP 论证 → ppt-master 21-25 页 SVG → PPTX。触发:用户要做"决策" / "下单" / "选产品" / "值不值" / "对比" / "对比一下" / "客群分流" 类 PPT,问"你确定拿到了" / "配色那么丑" / "站在旅客角度" / "做详细点分析到位点" / "图片也没插入" 时,本 skill 必走「7 项必走检查」防 v1 翻车。**默认必建 4 线对比表 (P06) + 3 张图集页 (P26-P28)**。
---

# 携程产品决策手册 PPT 工作流

> 给定产品 URL → 输出 21-25 页 16:9 PPT(旅客视角 / 多 MCP 论证 / 数据 4 色标记)
>
> 配套 skill: [ctrip-spa-capture](../ctrip-spa-capture/SKILL.md)(e2e 真抓)+ [ctrip-product-report](../ctrip-product-report/SKILL.md)(md 报告)+ [ppt-master](../../ppt-master/skills/ppt-master/SKILL.md)(SVG→PPTX)
> 配套 MCP 部署: [ctrip-spa-capture/references/mcphub-mcp-127-deploy.md](../ctrip-spa-capture/references/mcphub-mcp-127-deploy.md)(跨 docker + SDK 1.27 + bootstrap_v5)

## 0. Quality Bar — 用户反复要求的 4 个底色(必读,新会话也要从这开始)

> 用户在不同会话里 5+ 次说"做详细点 / 站在旅客角度 / 配色那么丑 / 你确定拿到了 / 分析到位点"。
> 这是**用户风格偏好**,不只是这次任务的需求。**新会话启动就按这 4 条走**,别等用户喊停。

| # | 底色 | 体现 | 反例 |
|---|---|---|---|
| 1 | **数据真实** | 价格/航班/酒店全部**真抓+溯源**(标"间接源"),不糊弄"已交叉验证" | 用 wendao 单一 LLM 总结当"独立第三方" |
| 2 | **旅客视角** | 关心什么列什么(违约损失/儿童/老年/护照/装备/天气) | 列内部字段,旅客看到"SH ID"="?" |
| 3 | **配色 + 排版** | 走 ppt-master 71 图表 / editorial 杂志感 / 海岛色,**别一上来自拼** | 纯色块矩形 + 居中白字,像 Word 模板 |
| 4 | **页数 + 密度** | 一页一个明确论点;不是 1 页塞 100 字也不是 30 页没信息 | 21 页可压到 10 页 / 标准 25-28 页 |

→ 详见 [quality-bar.md](references/quality-bar.md)(用户原话引文 + 反例 + 自查清单)

---

## 1. Eight Confirmations(8 字段确认,1 句话)

> ⚠ **MANDATORY — A 段 4 出行字段必须问齐再开跑**(2026-06-07 用户原话: "还需要预填 出发和返回日期呢")
>
> URL `?city=2` **只含 cityId**(=出发城市),**没有 fromDate/toDate/travelers**!
> 携程 m 端 SPA 默认展示"最近班期",**用户实际 7/4 是页面下拉选的**。
> **不预填 → PPT 价格日历展示错班期**(会把 7/11 当 7/4)。
>
> **A 段何时可省**: 用户消息里已给齐 4 字段(如"7/4 上海 2 人")→ 不问直接跑。
> **B 段 4 字段**: 有合理默认(26 页 / 杂志风 / 海岛色 / 16:9),**末尾"要不要改 X?"一钩子即可**。

收到产品 URL 后,**1 句话**问清 A 段 4 出行 + B 段 4 风格:

```
"<产品名> 已读 URL · 请确认:
【A 段 4 出行参数 · 必问】(URL 只含 cityId, 没有 fromDate/toDate/travelers)
  1. 出发城市=<> 2. 出发日=<> 3. 返程日=<> 4. 人数+客群=<>
【B 段 4 PPT 风格 · 默认即可】
  5. 页数=<> 6. 风格=<> 7. 配色=<> 8. 画布=<>
默认: 26 页 / editorial 杂志风 / 海岛蓝绿+火山橙红 / 16:9
"
```

| A 段字段 | URL 里有? | 必问? | 必问原因 |
|---|---|---|---|
| A1 出发城市 | ✅ `?city=2` 自动 = 上海 | ❌ 不用问 | URL 拿 |
| A2 出发日 | ❌ | ✅ **必问** | 携程默认"最近班期" ≠ 用户实际班期 |
| A3 返程日 | ❌ | ✅ **必问** | 同上 |
| A4 人数+客群 | ❌ | ✅ **必问** | 客群分流/装备清单/决策矩阵靠它 |

→ 详见 [eight-confirmations.md](references/eight-confirmations.md) 完整 4+4 字段表 + cityId 码表

### Step 0: 章节大方向先 1 句确认(别自己定)

> 用户初版要 10/12 页,后来加到 20+。**别自己定章节数 — 跟用户确认 1 句**:

```
"<产品名> 7 大块章节已设计:封面/价格日历/路线图/单日详情/竞品/预算/决策
预计 21 页(16:9),可压到 12 页或加到 30 页。改 X 吗?"
```

## 2. 工作流(8 步)

### Step 1: e2e 抓取(必走 ctrip-spa-capture)

```bash
python3 scripts/ctrip_spa_capture.py <productId> <cityId>
python3 scripts/extract_more.py <productId>   # 补 11 段被遗忘字段
```

产物:`/opt/data/ctrip-data/xhr_*.json` + `dom_text.txt` + `price_calendar_*.csv` + 4 类图片。

### Step 1.2: shoppingid + getShoppingDetail 抓 5 段真实酒店 + 航班(2026-06-07 新)

> **用户原话**: "shoppingid 是怎么拿到的,带上这个能拿到酒店和机票信息"
> **关键发现**: e2e 6 个 xhr json **不含 5 段真实酒店 + 真实航班班次**。这些在另一个 graphql 接口 **`getShoppingDetail`** 里,由 `shoppingid` 触发。
> **缺这一步 = P03 航班不准 / P06 真实酒店变 9 家备选**。

**4 大坑(踩过 2 次)**:
1. **URL 必须拼 `&shoppingid=32hex`**:不带 shoppingid 加载,SPA 不触发 getShoppingDetail graphql,所有 `response` 监听 0 抓,`expect_response` 也 timeout。
2. **必须用 `page.expect_response` 模式**:`page.on('response', ...)` 普通监听 0 命中(携程 SPA 用 fetch + AbortController,response 事件不可靠)。expect_response 是同步阻塞正确姿势。
3. **shoppingid 拿法**:① 从上次 e2e 抓的 `xhr_ProductInfo_2nd_V3_h5_<pid>.json` 里 `data.productInfo.ShoppingBasic.ShoppingId` ② fallback 用 URL 里 user 给的 ③ fallback 用 hard-code 32hex
4. **expect_response 一次只能等一个**:`for query in ['getShoppingDetail', 'getShoppingPrice']` 循环,每个都重新 `page.goto(url)` 触发

**必走流程**:
```bash
/opt/data/.venv/bin/python scripts/ctrip_shopping.py <productId> <cityId>
```
→ 输出 `xhr_getShoppingdetail_<pid>.json` (188 KB) + `xhr_getShoppingprice_<pid>.json` (124 KB)

**关键字段**:
- `data.shoppingDetail.Hotel.Hotels[].BasicInfo.Id` = 携程 SH ID (5 家真实酒店)
- `data.shoppingDetail.Hotel.Hotels[].BasicInfo.Name` = 酒店名
- `data.shoppingDetail.Flight.Segments[].Flights[]` = 真实航司班次 (GA895/G326/GA415/G894)
- `data.shoppingDetail.Flight.Segments[].Flights[].DepartInfo.DepartDateTime` = 真实起飞时间

→ 详见 [references/ctrip-shopping-detail.md](references/ctrip-shopping-detail.md) 完整 4 坑 + 退路 + 解析样本
### Step 1.3: 7 日 DOM 抓图文行程(2026-06-07 新)

> **用户原话**: "图文行程 日历行程 Email行程 打印行程 每日行程 都能提取得到吗"
> **关键发现**: 携程 SPA 把图文行程/日历/Email/打印/每日 5 个 tab 的数据 **塞在 DOM innerText**,不调 graphql。

**必走流程**:
```bash
/opt/data/.venv/bin/python scripts/ctrip_dom_7days.py <productId> <cityId>
```
→ 输出 `dom_text_7days_<pid>.txt` (~17 KB) + `dom_html_7days_<pid>.html` + `/tmp/ctrip_dom_7days.png`

**关键字段**(从 DOM text 解析):
- "Day\n01..07" + 主题标 + 早/午/晚餐 + 景点评分 + 酒店
- "违约金": 5%/20%/50%/60%/70% 退订阶梯(必须做 P20 退订风险页!)
- "费用包含": 6 早餐 + 1 午餐 + 7 日用车 + 接送机
- "自理费用": 巴厘岛旅游税 ¥75/人
- 景点评分: 赛武 5.0 / 布罗莫 5.0 / 伊真 4.9 / 水神庙 4.6 / 罗威纳 4.0 / 佩妮达 4.2

**3 大坑**:
1. **弹窗拦截**: 点击 tab 前要按 5 次 ESC + 遍历 `[class*="popup"]` `[class*="mask"]` 关掉所有 mask
2. **"图文行程" tab 在折叠区**: 用 `.first` 而不是 `page.locator('text=图文行程')` 全匹配
3. **DOM 滚到底**才完整:15 次 wheel 滚,再 `window.scrollTo(0, 0)` 回顶才抓

### Step 1.0: 一键跑全流程(2026-06-07 新)

```bash
./scripts/run.sh <productId> <cityId> [pageCount=26]
# 例: ./scripts/run.sh 69762187 2 26
```

`run.sh` 自动顺序跑 Step 1(e2e)→ 1.1(extract_more)→ 1.2(shoppingid)→ 1.3(7日DOM)→ 1.4(全量图)。
**已存在的文件自动跳过**,下次拿新 productId 重跑即可。

### Step 1.5: 下载并视觉分析产品图(必走,别漏)

> **2026-06-07 用户原话**: "你忘记要下载下来 分析的吗"
> 携程 SPA 抓取已自动下 16 张图到 `/opt/data/ctrip-data/img_<pid>/`,**别只看文字 JSON 就完事**。

```bash
# 看图清单(自动包含 4 类: desc banner × 3 + POI × 7 + PM × 1 + brand × 4)
cat /opt/data/ctrip-data/img_<pid>/manifest.json
ls -la /opt/data/ctrip-data/img_<pid>/
```

**必做 4 件事**:

1. **补下漏抓 4 类图**(extract_images.py 只抓 4 类,漏 hotel+comment+competitor+ranking = 45+ 张):
   ```bash
   /opt/data/.venv/bin/python scripts/dl_all_imgs.py <productId>
   ```
   → 详见 [all-image-sources.md](references/all-image-sources.md) + [scripts/dl_all_imgs.py](scripts/dl_all_imgs.py)

2. **精选 4-6 张复制到 ppt-master 项目** `images/` (封面图 + 关键 POI)

3. **用 M3 真视觉读图**(别用 `vision_analyze` 工具 — **它 server 端会 404**):
   - 改用 [scripts/m3_vision.js](scripts/m3_vision.js) 直调 minimax API
   - → 详见 [m3-native-vision.md](references/m3-native-vision.md) 模板 + 3 大坑

4. **嵌入 PPT** — 至少 P01 封面 = 主图全幅, P13-16 单日详情 = 1 图/页
   - **关键技术**: `<image href="data:image/jpeg;base64,..."/>` 嵌 SVG → rsvg 渲染 → ppt-master svg_to_pptx 自动编译
   - **必走 5 步**: ① M3 视觉精选 6-8 张图 → ② ffmpeg 缩 800px q=5(50-200KB/张)→ ③ base64 bundle 写 json → ④ SVG `<image>` 嵌 base64 → ⑤ ppt-master 编译
   - **必嵌 5 页**: P01 封面(主图全幅 + 渐变蒙版 + 白字)/ P06 真实酒店(主图 + 4 子图)/ P14 布罗莫(主图 + 行程表)/ P15 伊真(蓝火图 + 帐篷图)/ P16 佩妮达(主图 + 2 选 1 套餐)
   - **避坑**: 1) ffmpeg 800px q=5 平衡清晰度(50-200KB)+ base64 翻 1.33 倍(≤64MB body)2) 渐变蒙版 `<linearGradient>` + `<image preserveAspectRatio="xMidYMid slice"/>` 3) 暗色页(伊真 P15)用 #0F1A24 底 + #F5DEB3 字,亮色页用 #F5F1E8 米 + #1A1A1A 字
   - **M3 视觉问图模板**:
   - `desc_0.jpg` = 主图,问"画面内容 / 适合 PPT 哪一页"
   - POI 图问"这是哪个景点 / 适合放 P13-16 单日详情哪一页"
   - hotel 图问"酒店档次 / 适合放 P06 真实酒店页吗"
   - 营销 banner 问"完整提取所有文字 + 产品名 + 行程天数路线 + 价格 + 服务"

**重要: 别信文件名!** 携程 POI 字段名是营销标签,不是真实景点:`poi_爪哇岛.jpg` 实际是清真寺,不是布罗莫火山。M3 视觉读完再决定用不用。

→ 详细 [image-pipeline.md](references/image-pipeline.md) ffmpeg/rsvg 缩图 + PNG 预览命令链
→ 详细 [ppt-image-embed.md](references/ppt-image-embed.md) 5 步嵌图 + 5 页模板(2026-06-07 新)

### Step 2: 多 MCP 论证(不能省)

| MCP | 用途 | 失败时 fallback |
|---|---|---|
| **ctrip-mcp** (SPA e2e) | 主产品 / 班期 / 价格 / **图(自动 4 类)** | 重抓 1 次 |
| **wendao** | 气候 / 火山政策 / 真实评价 / 转车 | 携程主接口(标"间接源"!) |
| **AI_Go_Hotel_MCP** | 酒店坐标 / 区域 | 携程 InfrastructureInfoList |
| **variflight** | 航班实时(独立第三方) | **携程主接口 FlightInfoList (兜底, 标"间接")** |
| **amap** | 转车距离/时间估算 | wendao |

**关键: 每次调用完,把"结论+数据+来源"写进 md 的一个 working 表格**,作为 PPT 数据源。

> **2026-06-07 用户明确**: wendao = 携程缓存+AI 总结, **不** 等同独立第三方。
> 双源一致(携程主接口 × wendao) = **间接交叉**,必须显式标"间接",不糊弄"已交叉验证"。
> → 详见 [data-trust-tiers.md](references/data-trust-tiers.md) + [api-limitations.md](references/api-limitations.md)

### Step 3: 21-28 页章节模板(7 大块)

| 块 | 页 | 章节 | 数据源 |
|---|---|---|---|
| A 开篇 | P01-04 | 封面 / 目录 / 核心结论 / 真实航班 | URL + e2e + getShoppingDetail |
| B 行程 | P05 + P11-16 | 7 日概览 / 路线地图 / 单日详情 ×4 | dom_text_7days + wendao 转车 |
| C 价格 | P06-10 | 真实酒店 / 价格日历 / 7 月最低 / 班期 / 决策 KPI | getShoppingDetail + e2e + wendao |
| D 竞品 | P17 | 跟团游 vs 私家团 / 6 真实比价 | wendao 跟团游 |
| E 备料 | P18-22 | 班期库存 / 预算拆分 / 装备清单 / **退订风险** | e2e + FeeInfoList + dom 违约金 |
| F 决策 | P21-25 | 结尾 / 客群分流 / 风险预案 / 倒计时 / A/B/C 客群 | 综合 |
| (v2 增量) | P22-25 | 客群分流 + 风险 + 倒计时 + A/B/C 画像 | 4 真实在售产品 × 3 客群 |
| **(v4 增量)** | **P20** | **退订违约阶梯 5%/20%/50%/60%/70%** | **dom_text 违约金字段** |

> **2026-06-07 v4 新增 P20**: 必做退订风险页(柱状图 5 阶梯 + 3 大预案:航班变动/火山封/蓝火取消)
> 数据源是 dom_text_7days 里的"违约金"段,**没有这块 = 旅客不知道"7/3 23:59 后损失 ¥9,660"**

> 参考 [chapter-blueprint.md](references/chapter-blueprint.md)

### Step 4: 看 ppt-master 71 图表样例,自拼前先复用

> 用户原话: "配色那么丑 ppt-master 没有模版吗" —— 答案是**有 71 个**。
> **别一上来自己拼 SVG,先看 templates/charts/ 有什么现成**。

```bash
ls /opt/data/skills/ppt-master/skills/ppt-master/templates/charts/
```

高频已用: `bar_chart.svg · line_chart.svg · kpi_cards.svg · timeline.svg · matrix_2x2.svg · horizontal_bar_chart.svg · comparison_table.svg · waterfall_chart.svg`

**用法**: 打开对应 .svg,看 `<!-- chart-plot-area: x_min=...,y_min=...,x_max=...,y_max=... -->` 注释,直接改数据 + 改颜色 + 改文字。

**少拼的代价**: 7 大块章节中**至少 4 块可以 0 自绘**(价格日历/趋势/KPI/路线对比/竞品/库存/预算),剩下 3 块才自拼(封面/目录/路线地图)。
→ 详见 [ppt-master-71-charts-catalog.md](references/ppt-master-71-charts-catalog.md)

### Step 5: SVG 自拼(参考 design_spec + spec_lock)

**先写 design_spec + spec_lock**(13 色板 + 4 字体),**再写 SVG**。否则 quality_checker 会报 17+ 颜色未登记。

- [design_spec.md](templates/design_spec.md) — 设计规约
- [spec_lock.md](templates/spec_lock.md) — 颜色 + 字体 + 字号 锁定

**默认 13 色板**:
- 主: #1F4E79 蓝 / #3E6B53 绿 / #C0392B 红 / #D4A017 黄
- 文字: #1A1A1A(主) / #5C5C5C(辅)
- 背景: #FAF6EE 米 / #FFFFFF 卡 / #D4C5A0 边
- 数据: #1F4E79(正向) / #C0392B(反向)
- 海岛: #E8D9B5

**4 字体 stack**:
- `"Microsoft YaHei", sans-serif` 正文
- `Georgia, "Microsoft YaHei", serif` 标题
- `Consolas, "Microsoft YaHei", monospace` 数字
- `"Microsoft YaHei", "PingFang SC", sans-serif` 中文

### Step 6: 渲染命令链(必走 venv)

```bash
# 1. 质量检查(必须 0 error)
cd /opt/data/skills/ppt-master/skills/ppt-master
/opt/data/.venv/bin/python scripts/svg_quality_checker.py projects/<name>/svg_output/

# 2. finalize (圆角→Path, 文本 flatten)
/opt/data/.venv/bin/python scripts/finalize_svg.py projects/<name>/

# 3. svg_to_pptx (25 张 SVG → 16:9 PPTX)
/opt/data/.venv/bin/python scripts/svg_to_pptx.py "projects/<name>"

# 4. 复制到 workspace
cp projects/<name>/exports/<name>_<ts>.pptx /opt/data/home/workspace/<用户文件名>.pptx

# 5. 验证
/opt/data/.venv/bin/python -c "
from pptx import Presentation
p = Presentation('<path>.pptx')
print(f'{len(p.slides)} 页 · {p.slide_width/914400:.2f}x{p.slide_height/914400:.2f} 英寸')"
```

→ 详见 [ppt-master-usage.md](references/ppt-master-usage.md)

### Step 7: 5 个 SVG 坑(必查)

1. **XML well-formedness**:`&` 必须 escape 为 `&amp;`(踩过 1 次在 P20 "SECTION F · RISK & EXIT" 报错),其他 `&lt;` `&gt;` `&quot;` `&apos;` 也别用 HTML named entity `&nbsp;` `&mdash;` `&copy;`。Typography 字符用 raw Unicode(`—` `©` `→` NBSP)
2. viewBox 必须与画布尺寸一致
3. foreignObject: 用 `<text>` + `<tspan>` 手工换行
4. font-family stack 末尾必带 PPT-safe family(`Microsoft YaHei` / `Arial` / `Consolas`)
5. **image href 嵌 base64**:png/jpg 选其一,bundle 总大小 ≤ 5MB(超 64MB body 会爆 rsvg)

### v4 高质量策略(2026-06-07 经验,3-5 工具/turn 必走)

> **用户原话**: "现在从 0 走一遍流程 发一个高质量 PPT 给我"
> **不要重做 26 页新 SVG**(撑爆 quota)。改 5 张关键页 + 复用 v2/v3 其余 = 高水准 28 页 v4。

**5 张必改的关键页**(旅客视角 + 真图):
1. **P01 封面** = 主图全幅 + 渐变蒙版 + 杂志感标题
2. **P06 5 段真实酒店** = 主图 + 3 子图 + 5 段表(3 晚不可取消红标)
3. **P14 布罗莫+塞武** = 2 张真图 + 2 日行程表 + 4 大亮点
4. **P15 伊真** = 火山口 + 林塘玻璃穹顶 + 蓝火不保证风险框
5. **P16 佩妮达** = 精灵坠崖 + 钻石沙滩 + 2 选 1 套餐表
6. **(v4 新增) P20 退订风险** = 5 阶梯柱状图(0/5/20/50/60/70%)+ 3 大预案

**其余 22 张 v2 SVG 复用**(`cp projects/<v2>/svg_output/* projects/<v4>/svg_output/`),
改文件名为 v4 命名约定(`01_cover.svg` ... `25_customer_personas.svg`)。

→ 详见 [references/v4-high-quality-strategy.md](references/v4-high-quality-strategy.md) 5 张关键页 SVG 模板 + ffmpeg 缩图 + 编译命令链 + 5 坑

| 坑 | 症状 | 修法 |
|---|---|---|
| `&` 未转义 | Invalid XML | 改 `&amp;` |
| `marker-end="url(#xx)"` 无 `<marker>` | check ERROR | 改纯 `<line>` 或加 `<defs><marker>` |
| `symbol+use` 引用 | 渲染失败 | 改 inline |
| 同一元素 2 个 `font-size` 属性 | xml.etree "duplicate attribute" | 删 1 个 |
| spec_lock 颜色穷举 | 17+ 颜色未登记 | 先写 lock,后写 SVG |

**quality_checker 必须 0 error 才能进 finalize**。
→ 详见 [svg-pitfalls.md](references/svg-pitfalls.md)

### Step 8: 交付前自查(8 项)

- [ ] 21/25 页 全部 quality_check 0 error
- [ ] finalize_svg 成功
- [ ] svg_to_pptx 25/25 成功
- [ ] pptx 复制到 workspace
- [ ] 16:9 尺寸验证(13.33×7.5)
- [ ] 数据来源 4 色标记齐全
- [ ] v1 vs v2 差异表(若升级版)
- [ ] 用户原话硬约束:**"接口反爬 = 无解"** 不糊弄 / **"wendao = 间接"** 不写"独立验证"

---

## 3. 关联 skill 与资源

- **上游**:
  - [ctrip-spa-capture](../ctrip-spa-capture/SKILL.md) — 抓携程 SPA 主接口
  - [ctrip-product-report](../ctrip-product-report/SKILL.md) — Markdown 报告
- **下游(PPT 制作)**:
  - [ppt-master](../../ppt-master/skills/ppt-master/SKILL.md) — SVG → PPTX 工作流
- **外部 MCP**:
  - 携程-wendao(气候/政策,**间接源,必须标**)
  - AI_Go_Hotel_MCP(酒店)
  - 高德(距离)
  - variflight(独立航班,**不可用时降级**)

## 4. 缺失的思考(2026-06-07 全部跑通,v2 25 页已交付)

> 上一版 6 项全部 ✅ 跑通。**新发现 2 个真实瓶颈**也写进这里:

- [x] **航班数据库交叉验证** → wendao 实时 5 班次核实 + 修正 7/4→7/5 抵达
- [x] **点评时间分布** → 1 条 commentTime + extInfo 真实 takeoffDate (见 §Bottleneck 1)
- [x] **历史天气 30 天均值** → wendao 1981-2010 climate normal (泗水 31.5°C/15mm 旱季)
- [x] **实时汇率 USD/CNY** → 6.7878 (2026-06-07)
- [x] **客户体力画像问卷** → 4 真实产品 × 3 客群交叉(朋友 95% / 亲子 40% / 蜜月 80%)
- [x] **客群分流建议** → A 主推 7/4 / B 亲子 7/6 / C 蜜月 8/31
- [x] **风险 contingency plan** → 4 不可逆 + 4 Plan B(P23 整页)
- [x] **酒店升级路径** → 阿雅娜 5 钻 ¥1,000-2,000 加价 / 人
- [x] **决策时间倒计时** → 4 阶段 6/7-6/14 早鸟 → 7/3 急订(P24 整页)
- [x] **A/B/C 选项客群画像** → 携程 4 真实在售产品 × 3 客群(P25 整页)

### §Bottleneck · 真实硬件限制(诚实标注)

1. **航班"独立第三方"瓶颈**: variflight-mcp `getFlightTransferInfo` 报 `404 Invalid session id`(server 端 OAuth 挂);wendao = 携程缓存+AI 总结,严格意义上不算独立源。**当前用"携程主接口 FlightInfoList + wendao 5 班次"双源一致** 当间接交叉。**未实现真正独立源**(Trip.com / FlightConnections 浏览器反爬)。
2. **点评时间分布"接口反爬"瓶颈**: `getCommentSummary` 一次性只回 1 条详情(`comments[]` 长度=1,`totalCount=8` 但前 7 条不返)。`extInfo.extInfoMap` 含真实 `takeoffDate/returnDate`(已用,2026-03-28 团 = 真实样本)。**要拿全 8 条需分页 API(无页码参数 = 反爬设计),非"再查查"能解决**。
3. **产品图全量缺失瓶颈(2026-06-07 新)**: extract_images.py 只抓 4 类(16 张),**漏 hotel+comment+competitor+ranking = 45+ 张**。**e2e 抓的"行程酒店"数据是营销标签,不可信**,**必须 M3 视觉读图后**用真图。
4. **vision_analyze server 死**(2026-06-07 新): Hermes 内置 vision 工具 404/nginx,**改用 m3_vision.js 直调 minimax API**。
5. **m.ctrip.com/restapi/soa2 11010 Forbidden**(2026-06-07 新): 携程主接口全 403 反爬(沙盒 IP 黑)。**改用 AI_Go_Hotel_MCP searchHotels + getHotelDetail**(amap 后端,公开数据池),5 家 hotelId + 真实点评 + 房价全拿到,**无需 cookie 免登录**。`originQuery` 写中文意图 + `place` 必须**英文全名**(中文名常误配)。
6. **e2e 抓的"行程酒店"是营销标签**(2026-06-07 新): `imageHotelList` 9 家"备选"+ `HotelInfoList="自选酒店(4钻及以上)"` ≠ 真实入住。**真实 5 晚在图文日历**(用户贴的日历格式),`hotelList` URL 嵌 SH hotelId 段 → `AI_Go_Hotel_MCP.getHotelDetail(SHxxxxx)` 拿当日真实房型+价+距+评分。**P06 真实酒店页必须基于图文日历 5 家真,不能用 9 家备选**。

→ 详细 [api-limitations.md](references/api-limitations.md) 4 大原则 + 标注定式

## 4.5 Token 经济 — 工具调用硬约束

> Hermes 默认 max_iterations ≈ 90,本任务 21 页 SVG + 21 quality_check + 1 finalize + 1 svg_to_pptx = **~50 次工具调用**,逼近上限。**章节设计必须满足**:

1. **可压缩**: 简单产品压到 12 页(砍单日 + 砍 7 日概览 + 砍竞品)
2. **可拆分**: 7 大块各自独立,某一块出问题时只重做那块(不要整页返工)
3. **final-by-page**: 每一页 SVG 一旦写完,就不再改动(qa 用 quality_check 修,不要回写)
4. **优先复用 ppt-master 71 图表**: 自绘 = 多花 5-8 tool calls,复用 = 1 tool call 改数据
5. **产物先小后大**: 先 6 页 MVP 让用户看方向,再加 15 页深化(避免一次出 21 页返工)

## 4.6 章节大方向必须先 1 句确认

> 用户初版要 10/12 页,后来加到 20+。**别自己定章节数 — 跟用户确认 1 句**:

```
"<产品名> 7 大块章节已设计:封面/价格日历/路线图/单日详情/竞品/预算/决策
预计 21 页(16:9),可压到 12 页或加到 30 页。改 X 吗?"
```

> **不要连问 5 个 1+2+2+2+2**,用户会烦。**1 句话给推荐,问 1 件事**。

### 4.6.1 A 段 4 字段何时可省(2026-06-07 用户原问)

> **用户原话**: "还需要预填 出发和返回日期呢"
> **答案**: **必问,不能省** —— 携程 m 端 SPA URL **只带 productId + departCityId**,**没有 fromDate/toDate/travelers**!
> SPA 默认展示"最近班期",**用户实际班期是页面下拉选的**。

| 字段 | URL 里有? | 必问? | 必问原因 |
|---|---|---|---|
| A1 出发城市 | ✅ `?city=2` 自动 = 上海 | ❌ 不用问 | URL 拿 |
| A2 出发日 | ❌ | ✅ **必问** | 携程默认"最近班期" ≠ 用户实际班期,**不预填 → PPT 价格日历展示错班期** |
| A3 返程日 | ❌ | ✅ **必问** | 同上 |
| A4 人数+客群 | ❌ | ✅ **必问** | 客群分流/装备清单/决策矩阵靠它,**默认 2 成人/朋友不通用** |

**A 段可省的唯一情形**: 用户**消息里同时给完整 4 字段**(如 "7/4 上海 2 人 朋友") → **不问直接跑**。

**B 段 4 字段**: 有合理默认(26 页 / 杂志风 / 海岛色 / 16:9),**末尾"要不要改 X?"一钩子即可**。

## 4.7 先看 ppt-master 71 图表样例再自拼

> 用户原话: "配色那么丑 ppt-master 没有模版吗" —— 答案是**有 71 个**。**别一上来自己拼 SVG,先看 templates/charts/ 有什么现成**。

```bash
ls /opt/data/skills/ppt-master/skills/ppt-master/templates/charts/
```

高频已用(本次):
- bar_chart.svg · line_chart.svg · kpi_cards.svg · timeline.svg
- matrix_2x2.svg · horizontal_bar_chart.svg · comparison_table.svg · waterfall_chart.svg

**用法**: 打开对应 .svg,看 `<!-- chart-plot-area: x_min=...,y_min=...,x_max=...,y_max=... -->` 注释,直接改数据 + 改颜色 + 改文字。

**少拼的代价**: 7 大块章节中**至少 4 块可以 0 自绘**(价格日历/趋势/KPI/路线对比/竞品/库存/预算),剩下 3 块才自拼(封面/目录/路线地图)。

---

## 5. 关联 skill 与资源

- **上游**:
  - [ctrip-spa-capture](../ctrip-spa-capture/SKILL.md) — 抓携程 SPA 主接口
  - [ctrip-product-report](../ctrip-product-report/SKILL.md) — Markdown 报告
- **下游(PPT 制作)**:
  - [ppt-master](../../ppt-master/skills/ppt-master/SKILL.md) — SVG → PPTX 工作流
- **外部 MCP**:
  - 携程-wendao(气候/政策,**间接源**)
  - AI_Go_Hotel_MCP(酒店)
  - 高德(距离)
  - variflight(独立航班,**不可用时降级**)

## 6. References

- [quality-bar.md](references/quality-bar.md) — **用户反复要求的 4 个底色 + 自查清单(2026-06-07 新)**
- [eight-confirmations.md](references/eight-confirmations.md) — 8 字段锁定机制
- [chapter-blueprint.md](references/chapter-blueprint.md) — 21 页章节模板
- [ppt-master-usage.md](references/ppt-master-usage.md) — 命令链速查
- [ppt-master-71-charts-catalog.md](references/ppt-master-71-charts-catalog.md) — 71 图表自拼 vs 复用决策表
- [svg-pitfalls.md](references/svg-pitfalls.md) — 4 大坑 + 修法
- [data-trust-tiers.md](references/data-trust-tiers.md) — 真实度 4 色 + 源类型 3 分类
- [api-limitations.md](references/api-limitations.md) — **API 反爬 = 真实瓶颈,不糊弄"再查查"**
- [image-pipeline.md](references/image-pipeline.md) — 携程图下载/ffmpeg 缩图/vision 兜底链/嵌入 PPT 模板
- [m3-native-vision.md](references/m3-native-vision.md) — **M3 原生视觉直调 API**(vision_analyze 死时备胎,2026-06-07 新)
- [all-image-sources.md](references/all-image-sources.md) — **6 类图源全清单**(extract_more 漏 hotel+comment+competitor+ranking)
- [real-hotel-extraction.md](references/real-hotel-extraction.md) — **真实 5 晚酒店提取**(图文日历 + hotelList URL 解析 + AI_Go_Hotel_MCP 免登录查,2026-06-07 新)
- [case-p69762187-2026-07-04.md](references/case-p69762187-2026-07-04.md) — 本次案例
- [execution-checklist.md](references/execution-checklist.md) — 8 步可执行清单

## 7. Scripts

- [dl_all_imgs.py](scripts/dl_all_imgs.py) — 补抓 hotel+comment+competitor+ranking 4 类图(extract_images.py 漏的 45+ 张)
- [m3_vision.js](scripts/m3_vision.js) — M3 原生视觉直调 minimax API(vision_analyze 死掉时的备胎)
- [ctrip_shopping.py](scripts/ctrip_shopping.py) — 抓 shoppingid + getShoppingDetail (5 段真实酒店 + 航班) (2026-06-07 新)
- [ctrip_dom_7days.py](scripts/ctrip_dom_7days.py) — 抓图文行程 DOM (D1-D7 + 违约条款 + 6 早餐 1 午餐) (2026-06-07 新)
- [run_v4.sh](scripts/run_v4.sh) — v4 端到端 (7 参数: productId+cityId+fromDate+toDate+travelers+audience+pages) (2026-06-07 新)
- [run.sh](scripts/run.sh) — 旧版 2 参数一键跑 (productId+cityId)

## 8. v4 端到端用法 (run_v4.sh)

```bash
# 1 句命令, 4 出行参数预填
cd /opt/data/skills/ctrip-product-decision-deck
./scripts/run_v4.sh <productId> <cityId> <fromDate> <toDate> <travelers> <audience> [pages]
# 例: ./scripts/run_v4.sh 69762187 2 2026-07-04 2026-07-10 "2 成人" "朋友/双人" 26
```

`run_v4.sh` 内部跑:
- Step 1: e2e (ctrip_spa_capture.py)
- Step 1.1: extract_more.py
- Step 1.2: ctrip_shopping.py (5 段酒店 + 航班)
- Step 1.3: ctrip_dom_7days.py (7 日 DOM)
- Step 1.4: dl_all_imgs.py (60+ 张图)
- 输出 `spec.yaml` (含 4 出行字段 + 4 风格字段, 写进 ppt-master 项目)

**7 参数说明**:
1. `productId` — URL 里 `p69762187` 部分
2. `cityId` — URL `?city=2` 部分 (= 上海, 1=北京, 32=广州)
3. `fromDate` — 出发日 (YYYY-MM-DD)
4. `toDate` — 返程日 (YYYY-MM-DD, = fromDate + 行程天数 -1)
5. `travelers` — `"2 成人"` / `"1 大 1 童"` / `"退休夫妻"`
6. `audience` — `"朋友/双人"` / `"亲子"` / `"蜜月"` / `"退休"`
7. `pages` — 可选, 默认 26 (高水准) / 21 (标准) / 12 (精简)

### 8.1 run_v4.sh 失败时排错 (2026-06-07 教训)

> **用户原话**: "测试 (抓沙巴 64158367, ~25s)... JSONDecodeError: Expecting value: line 1 column 1 (char 0)"
> **教训**: 失败时**不要**只显示 traceback 末尾 (用户看不出真因),**必须** print head -40 + 4 个调试命令。

**v4 必走的错误显示模式**:
```bash
E2E_OUT=$("$VENV/bin/python" scripts/test_e2e.py 2>&1 || true)
if echo "$E2E_OUT" | grep -q "name:\|duration:\|saved"; then
  log "✓ e2e 通过" + tail -15
else
  warn "e2e 失败 — head -40 详细错误:"
  echo "$E2E_OUT" | head -40 | sed 's/^/  /'
  warn "调试命令 4 选 1:"
  warn "  1) sys.path: $VENV/bin/python -c 'import sys; print(sys.path[:3])'"
  warn "  2) chromium: ls /root/.cache/ms-playwright/chromium-1223/chrome-linux64/chrome"
  warn "  3) 网络: curl -sI https://m.ctrip.com/ | head -3"
  warn "  4) 直接调 spa_capture: $VENV/bin/python -c 'import asyncio, sys; sys.path.insert(0, \"$INSTALL_DIR/src\"); from ctrip_mcp.capture import spa_capture; print(asyncio.run(spa_capture(64158367, 2, scroll=True)))'"
fi
```

**test_e2e.py 必加 3 个增强** (2026-06-07 v5):
1. **导入失败诊断** — sys.path[:5] + `/opt/data/ctrip-mcp/src/ctrip_mcp` 是否存在
2. **text 长度检查** — `r1[0].text_len=0` 即时提示
3. **JSONDecodeError 显示前后文** — 头 200 字符 + 尾 200 字符 (定位是导入失败还是 API 返空)

## 9. Gitee 推 skill (2026-06-07)

仓库: https://gitee.com/weber-pan/ctrip-mcp (weber-pan SSH key 已配)
结构: AGENTS.md + skill/{ctrip-spa-capture, ctrip-product-report, ctrip-product-research, **ctrip-product-decision-deck (新)**}

**5 步推**:
```bash
# 1. 浅克隆
git clone --depth 1 https://gitee.com/weber-pan/ctrip-mcp.git /tmp/ctrip-mcp

# 2. 复制本地 skill 到仓库
cp -r /opt/data/skills/ctrip-product-decision-deck /tmp/ctrip-mcp/skill/

# 3. 改 AGENTS.md + README.md (3 skill → 4 skill)

# 4. 提交
cd /tmp/ctrip-mcp
git config user.name "weber-pan"
git config user.email "weber-pan@gitee.com"
git add skill/ctrip-product-decision-deck/ AGENTS.md README.md
git commit -m "feat(skill): add ctrip-product-decision-deck v4"

# 5. 推送
git push origin master
```

→ 详见 [gitee-publish.md](references/gitee-publish.md) 5 步 + 4 大坑 + 验证 3 步

## 10. v5 真实数据再抓后增量更新 pattern (2026-06-07 新)

> **场景**: 已经交付 v4 PPT(28 页)给用户, 用户给新 URL(如 p69762187)要"真实测试 + 完整 PPT"。
> 旧做法: 重新跑全套 (e2e + extract + shopping + dom + dl_imgs + Step 2-7 = **~50+ tool calls** + 28 张 SVG 重写, 撑爆 quota)
> **新做法**: 复用 v4 SVG, **只改 3-5 张关键页的文本/数据, 重打 PPTX** = **~20 tool calls** 搞定 28 页

### 10.1 何时走 v5 增量 (vs v6 全新)

| 信号 | 走 v5 增量 | 走 v6 全新 |
|---|---|---|
| 新产品 = v4 同一品类 (海岛/跟团游) | ✅ | |
| 新产品 = 全新品类 (城市观光/邮轮/单机票) | | ✅ |
| 7 大块章节布局相似 | ✅ | |
| 章节布局完全不同 (如 v4 是跟团游, v6 是邮轮) | | ✅ |
| 仅 3-5 张关键页价格/库存/酒店名变 | ✅ | |
| >10 页数据需重抓/重写 | | ✅ |

### 10.2 v5 增量 5 步 (≤20 tool calls)

```bash
# 1. e2e 抓新产品 (1 call) — 复用 run.sh 已有逻辑
python3 scripts/ctrip_spa_capture.py <newPid> <cityId>

# 2. 解析 (1 call) — 直接读 xhr json, 不要 mcp call (节省 1-2 call)
python3 -c "
import json
j = json.load(open('/opt/data/ctrip-data/xhr_VPC_SelectDateProductInfo_h5_<newPid>.json'))
# 提取: title, dailyMinPrices, minPriceRemark (5 段酒店 + 航班)
"

# 3. 复制 v4 SVG 框架到 v5 (1 call)
cp -r /opt/data/skills/ppt-master/skills/ppt-master/projects/cttrip_<oldPid>_v4_deck_<ts>/svg_final \
      /opt/data/skills/ppt-master/skills/ppt-master/projects/cttrip_<newPid>_v5_deck_<ts>/svg_final_v5

# 4. 改 3-5 张关键页 SVG 文本 (3-5 calls, patch 直接替换)
#   - P03 核心结论: 标题/价格/库存
#   - P07 价格日历: 7/1-7/3 价格 (e2e 抓的每日价)
#   - P08 7 月趋势: 加新最低日期
#   - P10 决策 KPI: 加库存数
#   - P22 双人预算: 加库存数

# 5. 重打 PPTX (1 call) — ppt-master svg_to_pptx 自动
cd /opt/data/skills/ppt-master/skills/ppt-master
python3 scripts/svg_to_pptx.py projects/cttrip_<newPid>_v5_deck_<ts> -s final
# → 28 张 0 fail

# 6. 复制到 workspace (1 call)
cp projects/.../exports/*.pptx /opt/data/home/workspace/<用户文件名>.pptx
```

### 10.3 SVG 文本替换模板 (patch in Python)

```python
import re
p = '/path/to/P07_price_calendar.svg'
txt = open(p).read()
# 改 7/1=8200 (旧) → 9159 (新), 7/2=8400 → 8592, 7/3=8892 → 8303
txt = txt.replace('>8200<', '>9159<', 1)
txt = txt.replace('>8400<', '>8592<', 1)
txt = txt.replace('>8892<', '>8303<', 1)
open(p, 'w').write(txt)
```

**核对模板** (改前先看):
```bash
grep -E "8948|8200|7893|库存" /path/to/P07.svg
# 期望: 8948 (7/4) + 7893 (7/6) + 8200/8400/8892 (7/1-3)
```

### 10.4 真实案例 (2026-06-07 p69762187 → v5, p69852382 → v1)

**p69762187 → v5 增量**(2026-06-07):
- v4 SVG 28 张在 `projects/cttrip_69762187_v4_deck_20260607_094641/svg_final/`
- 复制为 `svg_final_v5/` 加 README.md
- 改 3 张关键页: P07 (7/1-7/3 价格) + P08 (加 7/24 ¥7,649) + P10 (加库存 20)
- `python3 scripts/svg_to_pptx.py <proj> -s final` → 28/28 成功
- 复制 v5.pptx 到 workspace 交付

**p69852382 → v1 增量**(2026-06-07, 真实跑通):
- 复用 p69762187 v4 SVG 28 张, 改 6 张关键页: P01 封面 + P03 核心结论 + P07 价格日历 + P08 7 月趋势 + P10 KPI + P22 预算
- 总 tool calls: 13 (vs 重做全套 50+)
- **5 个新坑** (踩到并修了):
  1. **P03 `&` 未转义** (佩妮达&蓝梦) → 改 `&amp;`, 批量正则修全 28 张
  2. **P07 双人预算公式拼接错** (8948+8263+7893+... 残留) → 单独 patch 一次, re.findall 校验
  3. **`ctrip_get_product` 数据串台** (返回上一个产品名) → 改直接读落盘 JSON, 不走 mcp
  4. **`groupCard` 嵌套 None 又崩** (capture.py:250 parse_daily_min_prices 内部) → 双层 fallback `(pi or {}).get(...) or {}`
  5. **mcphub data_dir ≠ workspace** (返回"已落盘"但 workspace 读不到) → 走 `spa_capture()` 函数直调, 不走 mcp
- 完整 5 步 + 5 坑 + 12 个价格 mapping + 5 张关键页速查表见 [v5-increment-update.md](references/v5-increment-update.md)

### 10.5 v5 增量必避 3 坑

1. **别用 v4 价格作为新数据参考** — 价格日历按产品变, 每次 e2e 抓的最新价为准
2. **别重生成 28 张** — 复刻 v4 框架改 3-5 张 = quota 友好;重生成 = 5x tool calls + 不一定更好
3. **改完必跑 quality_checker** — `python3 scripts/svg_quality_checker.py <proj>/svg_final_v5/` 必须 0 error, 否则 finalize_svg 崩

### 10.6 与 vision 验证

- v5 PPTX 写完后,**不**用 `vision_analyze` 工具 (server 死) — 改 rsvg-convert 直接转 6 张关键页 PNG
- 用户要看封面/价格/酒店/预算页验证, **截图 1.7MB 1920x1080 PNG** 直接附
- 详细视觉走 m3_vision (m3-native-vision skill §1)

- [v5-increment-update.md](references/v5-increment-update.md) (5 步 + 3 坑 + 案例)
- [multi-line-4-bundle-compare.md](references/multi-line-4-bundle-compare.md) **4-线 subProductId 全对比 (2026-06-07 v2 教训: 用户质疑"只给了 A 线")**

---

## 10.7 v3 增量必抓: 官方图片 + P26-P28 图集页 (2026-06-07 p69852382 v3 教训)

**触发场景**: 用户做产品 PPT 且 PDF / 网页里有图(酒店/景点/点评), **必抓 4 类图 + 必建 3 张图集页**, 否则用户回"官方的图片也没插入到 ppt 里面啊"。

### 4 类必抓图 (走 ProductInfo JSON 1 次拿全)

抓完 `ctrip_spa_capture` 后, 读 `/opt/data/ctrip-data/xhr_ProductInfo_2nd_V3_h5_<productId>.json`:

| 类 | JSON 路径 | 数量 | 落盘 |
|---|---|---|---|
| **POI 景点** | `data.productInfo.imageStyleInfo.poiInfo.ImagePoiList[].imgUrl` | 10 | `ctrip_images/0N_poi_xxx.jpg` |
| **酒店实拍** | `data.productInfo.imageStyleInfo.hotelInfo.imageHotelList[].imageList[].imgUrl` | 1 家 3-5 张 | `ctrip_images/1N_hotel_xxx.jpg` |
| **点评头像** | `data.productInfo.commentInfo.comments[].userInfo.avatarUrl` | 2-5 张 | `ctrip_images/1N_avatar_xxx.jpg` |
| **产品 banner** | `data.productInfo.productExtend.MoreRecommendProductList[].ImageUrl` | 4-8 张 | `ctrip_images/1N_banner_xxx.jpg` (次要) |

```python
# 1 行下载 + 1 行优化
import requests
for url in urls: requests.get(url).content  # 写到 /opt/data/home/workspace/<proj>/ctrip_images/

# PIL 缩到 800x600 / quality 82 → 总 13 张图约 1 MB
from PIL import Image
im = Image.open(src); im.thumbnail((800,600), Image.LANCZOS); im.save(dst, 'JPEG', quality=82)
```

### 3 张必建图集页 (P26 + P27 + P28)

| 页号 | 内容 | SVG | base64 大小 |
|---|---|---|---|
| **P26 4 线图集** | A/B/C/D 4 张代表图 (景点/酒店各 1) | `26_4line_gallery.svg` | ~460 KB |
| **P27 酒店精选** | 主酒店 3 张实拍 (外部/房间/公共) | `27_hotel_gallery.svg` | ~430 KB |
| **P28 行程图集** | 9 个景点 3x3 网格 (D1-D6) | `28_itinerary_gallery.svg` | ~900 KB |

SVG 嵌图姿势: `<image x="0" y="0" width="400" height="300" href="data:image/jpeg;base64,XXXXX" />` → `svg_to_pptx` 自动解压到 `ppt/media/image_*.jpg`。

### 4 步必走 (10 min)

```
1. ctrip_spa_capture(product_id)  → 8 JSON (含 ProductInfo)
2. python 抽 4 类 URL → ctrip_images/all_data.json
3. requests 下载 + PIL 缩放 (1 MB) → ctrip_images/opt/
4. 建 svg/26/27/28 三张 → svg_to_pptx → 28/28 0 失败, pptx 内嵌 13 张图
```

### 教训收口 (本次 v1→v3)

- v1 漏 4 类图 + 漏 P26-P28 → 用户质疑"只给了 A 线" + "官方的图片也没插入"
- v2 加 4 线对比表, 但**仍未抓图**
- v3 抓 4 类图 + 建 3 张图集页 → **pptx 1.22 MB / 13 张图 / 28 页全绿**
- 守则: **产品 PPT 必带 ≥ 3 张图集页 + 4 类图必抓**
