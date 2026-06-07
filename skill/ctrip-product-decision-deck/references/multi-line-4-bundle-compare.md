# 多线产品 (subProductId 4-bundle) PPT 必走 · 4 线全对比

> **会话日期**: 2026-06-07 p69852382 v2 (从 v1 修来)
> **用户原话**: "你是不是只给了 A 线?" —— **v1 翻车教训**
> **触发场景**: 携程 SPA 抓 `groupCard.cards[]` 含 **2+ subProductId** 的产品(典型 4 线: 标准/升级/蜜月/联运)
> **核心规则**: **A/B/C/D 4 线必须并行抓 + 全程对比**,**不能只展示主推线 (A) 独占数据**

---

## 1. 为什么 v1 翻车了(踩坑时间线)

| 步骤 | v1 (错) | 缺什么 |
|---|---|---|
| e2e 抓取 | `ctrip_spa_capture(69852382)` 1 次 | 主产品 = A 线; B/C/D **不在同一份 JSON** |
| 4 线 subProductId 解析 | 拿 `groupCard.cards[].productId` 列表 = `[69852382, 69960194, 71330231, 63621261]` | ✅ 拿到 |
| **并行抓 4 线 product data** | ❌ **漏了**!只用了主产品的 `getByRelationId` 关联 | **B/C/D 的价格/酒店/航班全 0** |
| P03 核心结论 | 只放 A 线 7/4 ¥7,543 / 7/8 ¥5,886 | B/C/D 价 0 → **PPT 全是 A 线独占** |
| P07 价格日历 | A 线 7/1-7/31 价 | B/C/D 价 0 → **日历是 A 线单视角** |
| P10 决策 KPI | A 线 5 卡 (¥15,086 双人) | 决策 = **只比了 A 跟自己的非双人** |
| P22 双人预算 | A 线 ¥19,246 | B/C/D ¥0 → **旅客看不到 4 线比价** |
| → **用户发现**: "你是不是只给了 A 线?" | v1 整 28 页 A 线独占 | **修复 = 跑 v2** |

**根因**: 我**以为**主产品的 `VPC_SelectDateProductInfo_h5` 含所有 4 线的价格矩阵。**实际**:
- 主产品 JSON = **A 线的 VPC** (single line price)
- B/C/D = **各自独立 subProduct**,**必须并行抓 4 次** `ctrip_spa_capture(subProductId)` 才完整

---

## 2. 4 线并行抓取 (mcphub 推荐姿势)

```python
# 4 个 subProductId 并行调 ctrip_spa_capture (~33s × 4 = 132s, 但并行 ≈ 33s)
import asyncio
from mcp_servers.ctrip_mcp.capture import spa_capture

async def grab_all_lines(main_pid, sub_pids, city_id=2):
    """主产品 + 4 subProductId 并行抓取"""
    pids = [main_pid] + sub_pids
    results = await asyncio.gather(*[
        spa_capture(pid, depart_city_id=city_id, scroll=True, timeout=60)
        for pid in pids
    ], return_exceptions=True)
    return {pid: r for pid, r in zip(pids, results) if not isinstance(r, Exception)}

# 用法
LINE_PIDS = {
    'A': 69852382,  # 主产品 (高性价 5 钻)
    'B': 69960194,  # 小众秘境 4 晚海边别墅
    'C': 71330231,  # 2 晚阿雅娜 + 设计别墅专属包团
    'D': 63621261,  # 全国联运 + 双岛出海
}
all_data = asyncio.run(grab_all_lines(69852382, list(LINE_PIDS.values())[1:]))
```

**mcphub 直调姿势** (无需 Python 包装, 单线 1 call):

```python
# 在 execute_code 内 4 个并行调
import asyncio
async def grab(pid):
    return await mcp.call("ctrip_spa_capture", product_id=pid)

# 4 个 await
```

**Output**: 5 份 JSON (主产品 + 4 sub),各含:
- `xhr_VPC_SelectDateProductInfo_h5_<pid>.json` — 价日历 + 段酒店 + 航班
- `xhr_ProductInfo_2nd_V3_h5_<pid>.json` — 产品名/班期/退订
- `dom_<pid>.txt` — D1-D7 + 违约金

---

## 3. 4 线 7/4-7/10 价矩阵 (p69852382 v2 真实数据)

**从 4 份 VPC JSON 各抽 7/4-7/10 价**,拼成对比表:

| 日期 | A | B | C | D |
|---|---|---|---|---|
| 7/4 | 7543 | 9184 | 11793 | **None** ❌ |
| 7/5 | 8263 | 10154 | 12763 | None |
| 7/6 | 7993 | 9390 | 11993 | None |
| 7/7 | 6598 | 7905 | 10848 | **6259** ✓ |
| 7/8 | **5886** ★ | 7520 | 10398 | **5716** ★★ |
| 7/9 | 7483 | 9176 | 11761 | None |
| 7/10 | 7033 | 8674 | 11283 | None |

**关键发现** (旅客必看):
- D 线 7/4-7/10 **仅 7/7 ¥6,259 / 7/8 ¥5,716 / 7/11 ¥6,xxx** 班期 (3 天, 用户 7/4 不开!)
- 7/8 全场最低 ¥5,716 (D 线) + ¥5,886 (A 线) — 抢空风险 ★
- 双人总价 (7/4 出发): A ¥15,086 / B ¥18,368 / C ¥23,586 — **D 不开班**

**解析代码** (execute_code 内跑):

```python
import json, re
from pathlib import Path

DATA = Path('/opt/data/ctrip-data')
LINE_PIDS = {'A': 69852382, 'B': 69960194, 'C': 71330231, 'D': 63621261}
TARGET_DATES = [f'2026-07-0{i}' for i in range(4, 11)]

def extract_prices(pid):
    f = DATA / f'xhr_VPC_SelectDateProductInfo_h5_{pid}.json'
    if not f.exists(): return {d: None for d in TARGET_DATES}
    j = json.loads(f.read_text())
    pi = j.get('data', {}).get('productInfo', {})
    pcl = pi.get('PriceCalendar', [])  # ← 字段名按真实调整
    return {d: next((p['price'] for p in pcl if p.get('date') == d), None) for d in TARGET_DATES}

matrix = {line: extract_prices(pid) for line, pid in LINE_PIDS.items()}
# 算双人总价 (单程 4 线都是单人价, 双人 ×2)
for line, prices in matrix.items():
    valid = [p for p in prices.values() if p]
    print(f"{line} 7/4-7/10 双人预算 = ¥{valid[0]*2:,}" if valid else f"{line} 无班期")
```

---

## 4. v2 修法 (4 张关键页 + 1 张新页)

| 页 | v1 (错) | v2 (修) | 数据源 |
|---|---|---|---|
| **P02 目录** | 4 大块章节 + P03-P07 | 加 "4 线对比" 块, 路径 P03-P07 | — |
| **P03 核心结论** 02 行 | "A 线 ¥7,543 起" 单数 | "7/4-7/10 双人预算 A¥15,086 / B¥18,368 / C¥23,586 · D 仅 7/7 7/8 班期" | 4 线价矩阵 |
| **P06 (新页)** | v1 P06 = 5 段真实酒店 | **删除原 P06 → 新建 4 线对比表 (10-15 行 × 4-5 列)** | 4 线价矩阵 + 库存 |
| **P10 决策 KPI** | 5 卡 (A 线独占) | 4 卡 + 1 蓝条推荐: A/B/C/D 4 条线 7/4 单人 + 双人 + 推荐文字 | 4 线数据 |
| **P20 退订风险** | 5 阶梯柱状图 (A 线) | 5 阶梯 × 4 线柱 (4 色) | 4 线退订条款 |
| **P22 双人预算** | A 线 ¥19,246 | 加 "4 线预算" 行 | 4 线双人价 |
| **页脚 P01-25** | / 28 | / 29 (v2 缩 25 页, 但保留 28 页脚号, 验证 v1 残留) | — |

**P06 4 线对比表 SVG 模板** (新建 1 张, 10,625 字节):

```svg
<svg viewBox="0 0 1920 1080" ...>
  <text>4 线价格对比 · 7/4-7/10</text>
  <!-- 表头: 日期 | A 高性价 5 钻 | B 小众秘境 | C 阿雅娜专属 | D 全国联运 -->
  <g transform="translate(120, 200)">
    <text>日期</text><text>A</text><text>B</text><text>C</text><text>D</text>
  </g>
  <!-- 7 行: 7/4-7/10 -->
  <g transform="translate(120, 280)">
    <text>7/4</text><text>7,543</text><text>9,184</text><text>11,793</text><text>—</text> <!-- D 无班期标红 -->
    <text>7/5</text><text>8,263</text><text>10,154</text><text>12,763</text><text>—</text>
    ...
    <text>7/8</text><text>5,886 ★</text><text>7,520</text><text>10,398</text><text>5,716 ★★</text> <!-- 最低 2 星 -->
  </g>
  <!-- 双人 7 日总价 -->
  <g transform="translate(120, 800)">
    <text>双人 7 日预算</text>
    <text>A ¥15,086</text><text>B ¥18,368</text><text>C ¥23,586</text><text>D ¥11,432 (仅 2 天)</text>
  </g>
  <!-- 蓝条推荐 -->
  <rect x="120" y="900" width="1680" height="100" fill="#1F4E79"/>
  <text fill="#FFFFFF">RECOMMENDATION · 7/4 出发选 A · 7/8 全场最低 D ¥5,716 · 蜜月选 C 阿雅娜 2 晚</text>
</svg>
```

**P10 4 卡决策 SVG 模板**:

```svg
<svg viewBox="0 0 1920 1080" ...>
  <text>4 线决策卡 · 7/4 出发</text>
  <!-- 4 卡平铺 -->
  <g transform="translate(80, 200)"><rect width="430" height="600" fill="#FAF6EE"/>
    <text>A 高性价 5 钻</text>
    <text>¥7,543 单人 · ¥15,086 双人</text>
    <text>10 人团 · 5 晚别墅连住 · 15 景点</text>
    <text>推荐: 朋友 / 性价比党</text>
  </g>
  <g transform="translate(530, 200)"><rect ... fill="#E8D9B5"/>
    <text>B 小众秘境</text>
    <text>¥9,184 单人 · ¥18,368 双人</text>
    ...
  </g>
  <!-- 蓝条底部 -->
  <rect x="80" y="850" width="1760" height="80" fill="#1F4E79"/>
  <text fill="#FFF">综合推荐: 7/4 A 性价比 / 7/8 D 最低 (抢空风险) / 蜜月 C 顶级</text>
</svg>
```

---

## 5. 必走的 4 个检查 (v2 完工后)

1. **grep 验证 A 线独占字样** (避免漏改):
   ```bash
   # v1 残留: P03 "A 线 ¥7,543" / P07 "A 7/4=7543" / P10 "A 双人 ¥15,086"
   grep -E "A 线 ¥|A 双人|7/4 价 .7543" svg/P*.svg
   # v2 应输出 0 行 (或仅 P03 副标题保留 "A 线 5 钻纯玩")
   ```

2. **4 线数据齐全**:
   ```bash
   # 必须看到 4 个 subProductId 标识
   grep -E "69852382|69960194|71330231|63621261" svg/P*.svg
   ```

3. **页脚 / 28 → / 29 同步** (v2 缩 25 页, 但页脚统一):
   ```bash
   # 16 张 SVG 页脚批量改 (执行后已 0 残留)
   sed -i 's|/ 28|/ 29|g' svg/P*.svg
   ```

4. **残留 v4 SVG 清理** (复用 v4 时):
   ```bash
   # p69762187 v4 有 14_bromo/15_ijen/16_penida, p69852382 是单岛 → 必删
   rm -f svg/14_bromo.svg svg/15_ijen.svg svg/16_penida.svg svg/06_real_hotels.svg
   # 验: ls svg/ | wc -l = 25
   ```

---

## 6. 复用要点 (下一个 4-线产品直接 cp)

| 任务 | 操作 | 耗时 |
|---|---|---|
| e2e 抓主产品 (1 call) | `ctrip_spa_capture(main_pid, 2)` | ~33s |
| 并行抓 4 subProduct (4 calls) | `asyncio.gather` 4× `spa_capture(sub_pid, 2)` | ~33s (并行) |
| 解析 4 线 7 月价矩阵 (1 call) | 4 份 VPC JSON 抽 `PriceCalendar` | < 1s |
| 复用 v4 SVG 框架 (1 call) | `cp -r v4/svg_final v5/svg_final` | < 1s |
| 改 4 张关键页 SVG (4 calls) | patch P02/P03/P10/P22 + 新建 P06 | ~5 min |
| 删除 v4 残留 SVG (1 call) | `rm 14_bromo 15_ijen 16_penida 06_real_hotels` | < 1s |
| `svg_to_pptx` 25 张 (1 call) | 必 0 fail | ~10s |
| 4 张关键页 PNG 预览 (1 call) | `rsvg-convert` P03/P06/P07/P10 | ~3s |
| **总计** | | **~10 min / 14 tool calls** |

**vs 重做全套 28 张** = 50+ tool calls + 5x quota,**4 线增量 = 14 calls 省 70%**。

---

## 7. 红线 / 必避 5 坑

1. **❌ 用主产品 JSON 当 4 线价** — 主产品 = A 线, B/C/D 在 `groupCard.cards[].productId`,**必须各抓 1 次**
2. **❌ P03 写 "A 线 ¥X 起"** — 用户看不出 B/C/D,**必改 "X 价矩阵 A¥X / B¥X / C¥X"**
3. **❌ P10 5 卡 A 线独占** — 决策 = 至少 4 卡,各 1 线
4. **❌ 复用 v4 P14/15/16 火山页** — 4 线产品可能不是多岛,删
5. **❌ 漏标 "D 线 7/4 不开班"** — D 线 3 天班期是重大发现,旅客不知道 = 误订
