# 亚庇/沙巴 8 家 5 钻酒店 MCP ID 对照表

> 来源:携程 m 端 graphql `imageStyleInfo.hotelInfo.imageHotelList[]` + `AI_Go_Hotel_MCP-searchHotels` 交叉验证  
> 更新:2026-06-06  
> MCP 命中率:3/8 (凯悦尚萃/丹绒亚路香格里拉/艾美),其余 5 家走 wendao

## 8 家可自选酒店(携程产品 64158367 池)

| 携程 hotelId | 中文名 | 英文名(携程) | 5 钻级别 | MCP hotelId | MCP 覆盖 | 7/4-7/9 最低房价(5晚) | 携程点评 | 距市中心 |
|---|---|---|---|---|---|---|---|---|
| **706177** | 丹绒亚路香格里拉 | Shangri-La Tanjung Aru | 5 钻 | **46726** | ✅ | ¥11648(海景特大床) | 4.6/2700+ | 7.4km/机场10min |
| **706202** | 莎利雅香格里拉 | Shangri-La's Rasa Ria | 5 钻 | ❌无 | ❌ | 待查 | 4.6/2200+ | 30km |
| **706268** | 京那巴鲁凯悦 | Hyatt Regency Kinabalu | 5 钻 | ❌无 | ❌ | 待查 | 4.6/1600+ | 市区核心 |
| **97899535** | 凯悦尚萃 | Hyatt Centric | 5 钻 | **1579855** | ✅ | ¥4610(基础客房) | 4.7/1750+ | 市区核心 |
| **6286718** | 哥打京那巴鲁希尔顿 | Hilton Kota Kinabalu | 5 钻 | ❌无 | ❌ | 待查 | 4.4/900+ | 市区 |
| **21828508** | 哥打京那巴鲁万豪 | Marriott | 5 钻 | ❌无 | ❌ | 待查 | 4.3/500+ | 市区 |
| **132220733** | 哥打京那巴鲁喜来登 | Sheraton | 5 钻 | ❌无 | ❌ | 待查 | 4.5/800+ | 市区 |
| **706213** | 艾美 | Le Meridien | 5 钻 | **46738** | ✅ | ¥3120(城景基础) | 4.4/1600+ | 商场连通 |

## MCP 查询正确姿势

### 1. searchHotels(城市级搜索,找 hotelId)
```
AI_Go_Hotel_MCP-searchHotels({
  place: "Kota Kinabalu",
  placeType: "城市",
  originQuery: "查找亚庇 5 钻酒店, 7月4日入住 5 晚",
  size: 15
})
```
返回: hotelId + 最低价 + 星级 + 经纬度 + 评分 + 评论数
> 注意:结果跟携程 productId 不是同一套 ID,需要交叉匹配

### 2. getHotelDetail(精准查某酒店 7/4-7/9 房价)
```
AI_Go_Hotel_MCP-getHotelDetail({
  hotelId: 46726,  // 丹绒亚路香格里拉
  dateParam: {
    checkInDate: "2026-07-04",
    checkOutDate: "2026-07-09"
  },
  occupancyParam: {
    adultCount: "2",
    roomCount: "1"
  }
})
```
返回: 138 个 ratePlan(房型+价+退改)
> 注意:一个酒店 id 在这个接口返回 100-200 个 plan,要有过滤逻辑

### 3. 过滤低价 plan 的 Python 逻辑
```python
plans = inner['roomRatePlans']
plans_sorted = sorted(plans, key=lambda x: (x['totalPrice'] or 0))
seen = set()
for p in plans_sorted:
    cn = (p.get('roomNameCn') or p.get('roomName') or '?')[:30]
    price = p.get('totalPrice', 0)
    key = (cn, price // 100)
    if key in seen: continue
    seen.add(key)
    print(f"  ¥{price:>6}  {cn:<32s} ({p.get('bedTypeDescription','')[:15]})")
```

## MCP 未覆盖的 5 家酒店查法(wendao)

```bash
node /opt/data/scripts/wendao_query.js "亚庇 莎利雅香格里拉 Shangri-La's Rasa Ria 携程用户点评分(5分制)+点评数+主要差评"
node /opt/data/scripts/wendao_query.js "亚庇 京那巴鲁凯悦 Hyatt Regency Kinabalu 携程用户点评分+点评数+主要差评"
node /opt/data/scripts/wendao_query.js "亚庇 希尔顿 Hilton Kota Kinabalu 携程用户点评分+点评数+主要差评"
node /opt/data/scripts/wendao_query.js "亚庇 万豪 Marriott Kota Kinabalu 携程用户点评分+点评数+主要差评"
node /opt/data/scripts/wendao_query.js "亚庇 喜来登 Sheraton Kota Kinabalu 携程用户点评分+点评数+主要差评"
```

并发查:
```python
import subprocess
hotels = ["莎利雅香格里拉","京那巴鲁凯悦","希尔顿","万豪","喜来登"]
for h in hotels:
    q = f"亚庇 {h} 携程用户点评分(5分制)+点评数+主要差评"
    r = subprocess.run(["node","/opt/data/scripts/wendao_query.js", q],
                       capture_output=True, text=True, timeout=120)
    print(f"=== {h} ===")
    print(r.stdout[:500])
```

## 携程酒店评分 vs MCP 评分

| 酒店 | 携程 graphql 评分 | MCP score | 说明 |
|---|---|---|---|
| 丹绒亚路香格里拉 | 4.6/2700+ | 0(MCP 无) | 携程数据更准 |
| 凯悦尚萃 | 4.7/1750+ | 0(MCP 无) | 携程数据更准 |
| 艾美 | 4.4/1600+ | 0(MCP 无) | 携程数据更准 |
| 希尔顿 | 4.4/900+ | — | 携程数据 |
| 万豪 | 4.3/500+ | — | 携程数据 |

> MCP `searchHotels` 返回的 score 字段**全部是 0**(非仅缺失的 5 家),不可用。**酒店点评分以携程 graphql 或 wendao 为准**。

## getHotelDetail 结果读取规范

**MCP `getHotelDetail` 返回超大 JSON(117-150KB),工具输出被截断**:

```
输出示例:
{"success":true,"errorMessage":null,"hotelId":46726,...}
Full output saved to: /tmp/hermes-results/call_function_<id>_<n>.txt
```

**正确读取方式**:

```python
import json
raw = open('/tmp/hermes-results/call_function_<id>_<n>.txt').read()
j = json.loads(raw)           # outermost wrapper
inner = json.loads(j['result'])  # 真正数据在 result 字段
plans = inner['roomRatePlans']   # 房型列表
# 过滤逻辑(去重+排序)
plans_sorted = sorted(plans, key=lambda x: (x.get('totalPrice') or 0))
seen = set()
for p in plans_sorted:
    cn = (p.get('roomNameCn') or p.get('roomName') or '?')[:30]
    price = p.get('totalPrice', 0)
    key = (cn, price // 100)
    if key in seen: continue
    seen.add(key)
    print(f"  ¥{price:>6}  {cn:<32s} ({p.get('bedTypeDescription','')[:15]})")
```

> 注意:`result` 字段本身是**双重 JSON 字符串**,需要先 `json.loads(j['result'])` 再取字段。