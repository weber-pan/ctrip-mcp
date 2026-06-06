# Case: 携程 64158367 沙巴产品 4 条 sub-productId 逐线二次抓(2026-06-05)

## 触发点

主产品(ProductInfo_2nd_V3 主产品 64158367)抓完后,用户说:

> "四条线路 都获取了?你先概要的说一下 我看看真的拿到数据了没"

我只能确认 4 条线路的 `lineName / name / minPrice`(从 `groupCard.cards`),**但 B/C/D 3 条线的 D1-D7 详细行程文案我没拿到**。`TravelList[]` 数组只回 1 条 A 线的 TourInfoId。

## 走过的弯路(给未来 agent 警示)

### 弯路 A:以为 1 个主产品就够
- 答了 A 线的 D1-D7 行程,告诉用户"B/C/D 是 2 晚丹绒/3 晚海滨/全程同酒店"—— 用户马上反弹:"肯定 BCD 也要啊"
- 教训:**用户看到 4 条线卡片,默认要 4 条线全部展开**。报告不能只展开 1 条 + 1 句话解释另外 3 条

### 弯路 B:二次抓 B/C/D 的 ProductInfo_2nd_V3 拿到 200+KB JSON,以为数据全在
- 兴冲冲 `json.load` + walk,发现 `pi['BasicInfo']` 直接 KeyError
- 仔细看 `data.productInfo` 的 keys: `['elderFriendFlag', 'clientInfo', 'PriceInfo', 'productRanking', 'brandTag', 'imageStyleInfo', 'commentInfo', 'productExtend', 'compositeCoupon', 'CostInfoList', 'FeeInfoList', 'OrderKnow', 'Visa', 'SelfPayInfoList', 'PMRecomendInfo']`
- **sub-product 跟主产品返回的 graphql 字段集不一样**——**没有 BasicInfo/TravelList/TravelIntroductionInfo/priceCalendar**
- 关键差异:

  | 字段 | 主产品 | sub-product |
  |---|---|---|
  | BasicInfo(目的地/出发地) | ✅ | ❌ |
  | TravelList(逐日 TourInfo) | ✅ 1 条 | ❌ |
  | TravelIntroductionInfo(D1-D7 长文) | ✅ | ❌ |
  | priceCalendar(7 月全月价) | ✅ | ❌ |
  | FeeInfoList(费用含/不含) | ✅ | ✅(同结构) |
  | commentInfo(点评) | ✅ | ✅(共用主产品) |
  | imageStyleInfo(8 家酒店) | ✅ | ❌(从主产品拿) |

### 弯路 C:想在 sub-product JSON 里硬找"行程"字段
- 翻了 CostInfoList / SelfPayInfoList / OrderKnow / Visa,都没有 D1-D7
- 原因:sub-product 只是个"配置壳",**真正的 D1-D7 行程文案是页面渲染时 DOM 拼出来的**

## 正确路径(2026-06-05 验证)

### Step 1:从主产品 `TourGroupInfo` 拿到 4 个 sub-productId

```python
import json
j = json.load(open('/opt/data/ctrip-data/xhr_graphql_VPC_SelectDateProductInfo_h5.json'))
for p in j['data']['productInfo']['TourGroupInfo']['TourGroupProductInfo']:
    print(p['ProductId'], p['Description'])
# 64158367  3+2 组合,双酒店随心任选         ← sort 1, 主产品
# 38789419  高端升级--2晚丹绒香格里拉        ← sort 2, B 线
# 73810124  2 晚热销+3晚海滨度假酒店          ← sort 3, C 线
# 73810123  全程同酒店入住,无需舟车劳顿      ← sort 4, D 线
```

### Step 2:对 3 个 sub-product 各跑一次 ctrip_spa_capture.py(二次抓)

`ctrip_spa_capture.py` 当前版本只支持单 productId,**二次抓需要手动改写或者调下面这版**(我后来在脚本里加了 `--multi` 参数,但本次 session 是手跑 3 次的):

```python
import json
for tag, pid in [("B_38789419", 38789419), ("C_73810124", 73810124), ("D_73810123", 73810123)]:
    # ... 跑一次 SPA capture,产物 dom_<tag>.txt + xhr_<tag>_2nd.json
```

### Step 3:从 DOM 文本抽 D1-D7

```python
import re
for tag, fn in [("B","dom_B_38789419.txt"), ("C","dom_C_73810124.txt"), ("D","dom_D_73810123.txt")]:
    t = open(f'/opt/data/ctrip-data/{fn}').read()
    days = re.findall(r'D\d\|[^\n]{0,500}', t)[:7]
    for d in days: print(f"  [{tag}] {d[:300]}")
```

### Step 4:从主产品 dailyMinPrices 拿 4 条线 7/4 分价

不需要再抓 4 次价格——主产品 `priceCalendar.dailyMinPrices[]` 已经齐全:

```python
for d in pi['priceCalendar']['dailyMinPrices']:
    if d['hotelDate'] == '2026-07-04':
        for pp in d['productPrices']:
            print(f"  subId={pp['productId']}  ¥{pp['price']}")
# 64158367  ¥6858   A 线
# 38789419  ¥8402   B 线
# 73810124  ¥7294   C 线
# 73810123  ¥6840   D 线
```

## 4 条线 D1-D7 真实差异(2026-06-05 沙巴案例)

| Day | A 线 | B 线 | C 线 | D 线 |
|---|---|---|---|---|
| **D1** | 抵达亚庇,专车接机 | 同 | 同 | 同 |
| **D2** | 市区+丹绒日落(8 景点+三色果汁) | 同 | 同 | 同 |
| **D3** | 淘梦岛出海一日游 | 同 | 同 | 同 |
| **D4** | 自由活动(可加购) | **入住丹绒亚路香格里拉** | 自由活动+换海边度假酒店 | 自由活动 |
| **D5** | 自由活动 | 自由活动 | 自由活动 | **入住丹绒亚路香格里拉** |
| **D6** | 自由活动 | 同 | 同 | 同 |
| **D7** | 送机 | 同 | 同 | 同 |

**真正的差异只在 D4-D5 哪一天住哪家**。

## 复用模板

未来做"携程产品 p<id> 4 条线路"任务:

```bash
# 1. 主产品一次抓
/opt/hermes/.venv/bin/python /opt/data/skills/devops/ctrip-product-research/scripts/ctrip_spa_capture.py <mainId> <deptCity>

# 2. 拿到 sub-productId 列表
python3 -c "
import json
j = json.load(open('/opt/data/ctrip-data/xhr_graphql_VPC_SelectDateProductInfo_h5.json'))
for p in j['data']['productInfo']['TourGroupInfo']['TourGroupProductInfo']:
    print(p['ProductId'], p['Description'])
"

# 3. 逐个 sub-product 二次抓(循环)
/opt/hermes/.venv/bin/python /opt/data/skills/devops/ctrip-product-research/scripts/ctrip_spa_capture.py <subId1> <deptCity>  # → dom_<id>.txt
/opt/hermes/.venv/bin/python /opt/data/skills/devops/ctrip-product-research/scripts/ctrip_spa_capture.py <subId2> <deptCity>
/opt/hermes/.venv/bin/python /opt/data/skills/devops/ctrip-product-research/scripts/ctrip_spa_capture.py <subId3> <deptCity>

# 4. 抽 D1-D7
python3 -c "
import re
for tag, fn in [('B','dom_B_<id>.txt'),('C','dom_C_<id>.txt'),('D','dom_D_<id>.txt')]:
    t = open(f'/opt/data/ctrip-data/{fn}').read()
    for d in re.findall(r'D\d\|[^\n]{0,500}', t)[:7]: print(f'  [{tag}] {d[:200]}')
"

# 5. 4 条线 7/4 班期价从主产品 priceCalendar 一次性拿
# (见上面 Step 4)
```

## 不要重蹈

- ❌ 不要以为"抓了主产品就等于抓了所有线路"——4 条线是 4 个独立 sub-productId
- ❌ 不要在 sub-product 的 `data.productInfo` 找 `BasicInfo/TravelList/priceCalendar`——这些字段 sub-product 不返回
- ❌ 不要把"主产品 D1-D7 行程文案"当所有 4 条线都一样的行程——A/B/C/D 至少 D4-D5 有差异(哪天换酒店)
- ❌ 不要忘了 DOM 文本里 `D1|📍...` 这种 emoji 标记是**唯一**稳定的逐日锚点,正则 `D\d\|[^\n]{0,500}` 一抓一个准
- ❌ 不要给用户展示"4 条线名+起价"就完事,必须展示"D1-D7 4 线路对照表"
