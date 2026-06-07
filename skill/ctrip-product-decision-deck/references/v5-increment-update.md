# v5 增量更新实战模式 — p69852382 真实案例 (2026-06-07)

> 适用: 已经交付 v4 PPT, 用户给同品类新 URL (海岛/跟团游) 要"完整 PPT"。
> 旧: 重新跑全套 = 50+ tool calls 撑爆 quota。
> 新: 复用 v4 SVG 框架, 改 5 张关键页 = ~20 tool calls。
> **本文档基于 p69852382 巴厘岛 7 日 5 晚 真实跑通, 记录 5 个踩坑。**

## 1. v5 增量触发条件(决策表)

| 信号 | 走 v5 增量 | 走 v6 全新 |
|---|---|---|
| 新产品 = v4 同一品类(海岛/跟团游) | ✅ | |
| 7 大块章节布局相似 | ✅ | |
| 仅 3-5 张关键页价格/库存/酒店名变 | ✅ | |
| 新产品 = 邮轮/单机票/城市观光 | | ✅ |
| >10 页数据需重抓/重写 | | ✅ |

**本次案例**: p69762187 巴厘岛+泗水+布罗莫 → p69852382 巴厘岛 7 日 5 晚, **同品类同布局** → 走 v5 增量, 28 页全复用, 改 5 张关键页。

## 2. v5 增量 5 步法(≤20 tool calls)

### Step 1: e2e 真抓新数据(1-2 calls)

**必走 mcphub 调 `ctrip_spa_capture`**:
```python
mcp_mcphub_smart_call_tool(toolName="携程官网-ctrip_spa_capture",
                             arguments={"product_id": 69852382})
```

**坑 1**: `ctrip_get_product` 在 mcphub 调用时**会复用上次缓存的 JSON**! p69852382 调用时**返回的是 p69762187 的数据**(name 错! 价格是 8948 而非 7543)!

**症状定位**:
- `product_basic.name` 是其他产品名 → 99% 是缓存
- `price` 数量级不对(2 个 0 的偏差) → 同上

**修法**:
- 别用 `ctrip_get_product` 拿结构化数据 → 改**直接读落盘 JSON**:
```python
import json
vpc = json.load(open('/opt/data/ctrip-data/xhr_VPC_SelectDateProductInfo_h5_<pid>.json'))
```
- 7-8 个 xhr 文件都是真抓, **但 `TourGroupInfo.groupCard` 等嵌套字段在单线产品常为 None**(坑 4)。

### Step 2: 解析关键字段(1 call, 内存里)

```python
# 价格日历: productInfo.priceCalendar.dailyMinPrices
# minPriceDate: /Date(1783440000000+0800)/ = 2026-07-08
# 7/1-7/31: 31 个 dailyMinPrices (每个含 price/inv/showGroup)
# 班期 (showGroup=True) ★ 标: 7/8 ¥5886 inv=5, 7/10 ¥7033 inv=49
# groupCard: 4 条线 (A/B/C/D 各自 productId + displayPrice + lineName)

# 4 条线 (groupCard 字段) 提取模板:
for card in groupCard:
    print(f"{card['lineName']}: ¥{card['priceInfo']['displayPrice']} ({card['tagInfo'].get('travelServiceTagList', [{}])[0].get('tagName', '?')})")
```

**真实数据(p69852382)**:
| 线 | 名字 | displayPrice | bestTag | 团型 |
|---|---|---|---|---|
| A 69852382 | 高性价5钻 | ¥5,836 | 住宿更优 | 10人 |
| B 69960194 | 4晚海边别墅 | ¥7,409 | - | 10人 |
| C 71330231 | 2晚阿雅娜+别墅 | ¥10,348 | 团队规模小 | 5人 |
| D 63621261 | 全国联运 | ¥5,254 | 住宿更优 | 10人 |

### Step 3: 复制 v4 SVG 框架(1 call)

```bash
# 软链方式 (最省 quota)
ln -s /opt/data/home/workspace/p<new>/svg \
      <v4-proj>/svg_final

# 跑完打包后记得还原:
rm <v4-proj>/svg_final
mv <v4-proj>/svg_final_v4_backup <v4-proj>/svg_final
```

### Step 4: 改 5 张关键页 SVG(3-5 calls)

**必改的 5 张**(从 v4 → v5):
- P01 封面: 产品名/天数/价格/景点数
- P03 核心结论: 5 行全部
- P07 价格日历: 7/1-7/12 价格 (mapping 替换 12 个)
- P08 7 月趋势: 加新最低日期
- P10 决策 KPI: 5 卡全替
- P22 预算: 跟团价/自费/eVOA/小费/旅游税

**Patch 模板**:
```python
p = '/path/to/P07.svg'
txt = open(p).read()
mapping = {
    "9159": "6148",   # 7/1
    "8592": "7543",   # 7/2
    ...
    "¥8948": "¥7,543",  # 7/4
}
for k, v in mapping.items():
    txt = txt.replace(k, v)
open(p, 'w').write(txt)
```

### Step 5: 打包 PPTX(1 call)

```bash
cd /opt/data/skills/ppt-master/skills/ppt-master
python3 scripts/svg_to_pptx.py <v4-proj> -s final
# → 28/28 成功
```

## 3. 5 个真实坑(本次踩到)

### 坑 1: SVG `&` 未 escape,打包崩

**症状**:
```
xml.etree.ElementTree.ParseError: not well-formed (invalid token):
line 30, column 180
```

**原因**: 修改 P03 文字时写了 "佩妮达&蓝梦", `&` 是 XML 保留字符, 必须 `&amp;`。

**修法**(自动批量修):
```python
import re, os
dst = '/path/to/svg'
for f in os.listdir(dst):
    if not f.endswith('.svg'): continue
    txt = open(f'{dst}/{f}').read()
    new = re.sub(r'&(?!amp;|lt;|gt;|quot;|apos;|#)', '&amp;', txt)
    if new != txt:
        open(f'{dst}/{f}', 'w').write(new)
```

**二次踩坑**: SKILL.md §SVG pitfalls 1 提到 "P20 'SECTION F · RISK & EXIT' 报错", **但 P03 也会撞** (用了 "佩妮达&蓝梦" 同样未转义)。**必查 P03 5 行结论 + 行程文字**。

### 坑 2: P07 价格公式拼接错(手滑)

**症状**: 替换完 7/1-7/10 价格后, 双人预算公式变成了:
```
8948+8263+7893+6598+¥5,886+7483+7033 = ¥58,614 / 7 = ¥8,373 平均
```
但 v4 旧 P07 的 mapping 是 9159/8592/8303 → 8948/8394/7893, **新数据是 7543/8263/7993**, 8,948 是 v4 旧值, 8,373 平均也对不上。

**原因**: 旧 mapping 残留(`"8632": "¥5,886"` 把 v4 的 7/8 当成了 7/6), 后面又叠加了旧 prefix。

**修法**:
- 双人预算公式**单独 patch** 一次, 不在 mapping 里
- 改完 **verify**:
```python
import re
m = re.findall(r'\d+,\d+\+\d+,\d+\+', txt)
print('公式段:', m)
# 期望: ['7,543+8,263+', '6,598+5,886+', '7,033 = ']
```

### 坑 3: `ctrip_get_product` 数据串台

**症状**: 调用 `ctrip_get_product(69852382)` 返回的 `product_basic.name = "印度尼西亚巴厘岛+泗水+布罗莫+佩妮达 7日6晚"`(p69762187 的!)

**原因**: mcphub 包装的 tool 实现里, **call_tool 实际复用了上次落盘的 JSON**(可能是因为 ProductInfo 文件同名了或缓存)。

**修法**:
- 解析关键字段**直接读落盘 JSON**:
```python
vpc = json.load(open('/opt/data/ctrip-data/xhr_VPC_SelectDateProductInfo_h5_<pid>.json'))
productInfo = vpc['data']['productInfo']
daily = productInfo['priceCalendar']['dailyMinPrices']
segments = productInfo['Segments']
groupCard = (productInfo.get('TourGroupInfo') or {}).get('TourGroupProductInfo') or []
```

### 坑 4: groupCard 嵌套 NoneType 又崩

**症状**: `parse_daily_min_prices` 内部 `pi.get("TourGroupInfo", {}).get("TourGroupProductInfo", [])` → None 链式 .get 崩。

**根因**: p69762187 修过**主接口的 TourGroupInfo**, 但 `parse_daily_min_prices` 内部有一份独立 groupCard 取 line_names 的代码, **没修**。

**修法**(p69762187 fix 类似, 双层 fallback):
```python
# 旧 (崩):
tgi = pi.get("TourGroupInfo", {}).get("TourGroupProductInfo", [])

# 新:
tgi = (pi.get("TourGroupInfo") or {}).get("TourGroupProductInfo") or []
```

**已修**(2026-06-07, capture.py:250) 并推到 gitee `14c8679`。

### 坑 5: mcphub 端 data_dir 跟 workspace 不同, DOM 不全

**症状**: mcphub `ctrip_spa_capture` 返回 "已落盘" + "dom 16,658 字符", 但 workspace 端读 dom 文件是 17 KB(完整 7 日行程), **从 mcphub 容器路径读不到**。

**原因**: 
- mcphub 容器有自己的 data_dir(`/opt/data/ctrip-data/`), 在 mcphub 容器里写
- workspace(`/opt/data/ctrip-data/`)是另一只读挂载
- 通过 `spa_capture()` 函数直接调时, 走**进程 cwd 下的 data_dir** 写, 是 workspace 路径

**修法**:
- 走 `spa_capture(<pid>, <cityId>, ...)` 函数直调(不经过 mcp 包装)→ 落到 workspace
- 需要在 workspace 端跑, **不要**走 mcp call (它会写到 mcphub 容器路径)

## 4. SVG 文本替换速查表(p69852382 真实数据)

### P01 封面
| 改 | 旧 | 新 |
|---|---|---|
| 天数 | 印尼 7 日 6 晚 | 印尼 7 日 5 晚 |
| 副标 | 巴厘岛+泗水+布罗莫+伊真+佩妮达 | 巴厘岛 A 线 5 钻纯玩 |
| POI | Nusa Penida·Bromo·Ijen·Lovina·Tegallalang | Nusa Penida·Lembongan·Ubud·Jimbaran |
| 价 | ¥13,800 起/人 | ¥7,543 起/人 |
| 钻 | 4-7 钻酒店 | 5 钻泳池别墅 |
| 景点 | 6 大景点 | 15 个景点 |
| 团型 | 2 人成行 | A 线 10 人团 |
| pid | p69762187 | p69852382 |

### P03 核心结论(5 行)
| 行 | 旧 | 新 |
|---|---|---|
| 01 产品 | 巴厘岛+泗水+布罗莫+佩妮达 7 日 6 晚 | 巴厘岛 7 日 5 晚 私家团·A 线 5 钻纯玩 (No.1) |
| 02 价格 | 7/4 ¥8948/双人 ¥17,896, 7/6 最低 ¥7893 | 7/4 ¥7,543/双人 ¥15,086, 7/8 整月最便宜 ¥5,886(库存 5!) |
| 03 体力 | 凌晨 3 点爬布罗莫 200 阶·伊真蓝火已关 | 轻松海岛游·全程 5 钻泳池别墅·双出海+浮潜+漂流 |
| 04 航班 | 7/4 无 SHA→SUB 直飞·7/4 飞 HKG 住一晚 | MU5029/30 东航直飞·7/4 当日可达 |
| 05 酒店 | 桑提卡固本/布罗莫/外南梦/罗维纳/库塔 | 金巴兰叶子豪华别墅 (5 晚 5 钻 100 平别墅) |

### P07 价格日历
12 个价格替换 + 1 个公式替换 + 1 个班期提示替换

### P08 7 月趋势
- 7/4 价: ¥8,948 → ¥7,543
- 7/6 ¥7,893 → 7/8 ¥5,886 ★
- 全年最低价段: 5 个值替换
- 退路推荐: 改成 "7/8 (库存 5), 7/10 (★), 8/28 (全年最低)"

### P10 KPI 5 卡
- 行程天数: 7 天 6 晚 → 7 天 5 晚
- 景点数: 16 → 15
- 真实酒店: 5 晚 4 钻+(库塔降级) → 5 晚 5 钻(全程同酒店)
- 真实航班: 4 段国泰 CX → 2 段东航 MU5029/30
- 7/4 双人: ¥17,8948 × 2 → ¥15,086 (7543 × 2)
- 决策分数: 8.5/10 → 9.0/10

### P22 双人预算
- 跟团: ¥17,896 (8948×2) → ¥15,086 (7543×2)
- 自费: ¥2,500 (浮潜+追豚+蓝火) → ¥1,800 (浮潜+追豚+漂流)
- eVOA: ¥700 (35 美金×2) → ¥500 (25 美金×2)
- 备用+杂费: ¥1,520 → ¥1,360 (含旅游税 15 万印尼盾 × 2)
- 小费: ¥420 (7 天 × 60/人) → ¥500 (7 天 × 70/人)
- 总计: ¥23,036 → ¥19,246

## 5. 5 个坑速记卡(贴墙版)

```
[坑 1] & 未转义 → XML 错
  修: re.sub(r'&(?!amp;|lt;|gt;|quot;|apos;|#)', '&amp;', txt)
  高发: P03 核心结论 5 行文字 + P14-16 行程详情

[坑 2] P07 公式拼接错
  修: 单独 patch 一次 + 跑完用 re.findall 校验
  高发: 改 mapping 12 个价格时, 双人预算公式常被污染

[坑 3] ctrip_get_product 数据串台
  修: 直接读落盘 JSON, 不走 mcp call
  症状: 返回的是上一个产品的数据

[坑 4] groupCard 嵌套 None
  修: (pi or {}).get(...) or {} 双层
  必查: capture.py:250 (parse_daily_min_prices 内部) + server.py:200 (get_product)

[坑 5] mcphub data_dir ≠ workspace
  修: 走 spa_capture() 函数直调, 不走 mcp call
  症状: 返回"已落盘"但 workspace 读不到
```

## 6. 工具调用预算

本次 p69852382 真实跑通总 tool calls:
- 1 (health/spa_capture mcphub) + 1 (get_product mcphub, 串台发现) + 1 (spa_capture 直调) + 1 (解析 1) + 1 (cp SVG) + 5 (patch P01/P03/P07/P08/P10/P22) + 1 (& escape) + 1 (svg_to_pptx) + 1 (cp PPTX) = **~13 tool calls**
- 对比 v4 重做全套 50+: **节省 70%+**
