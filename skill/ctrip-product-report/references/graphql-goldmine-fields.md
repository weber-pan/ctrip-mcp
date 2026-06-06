# 携程 graphql "金矿字段"挖掘清单 (p42461732 + p64158367 实测)

> 来源: 2026-06-06 p42461732(印尼布罗莫) + 2026-06-05 p64158367(沙巴)两次真抓后,对比 `ProductInfo_2nd_V3_h5.json` 顶层 34 个字段
> 用途: 报告生成时**必查**这些字段,7 段式 → 11 段式

## 5 个"被遗忘但金矿"的字段

### 1. `expertInfo.datas[]` — 携程社区 10 条攻略文章 ⭐⭐⭐

**这是金矿中的金矿** — 携程给每个产品配 10 条社区内容(标题+作者+图+点赞+跳转链接),产品页"攻略"模块的源。

```python
j = json.load(open('xhr_graphql_ProductInfo_2nd_V3_h5.json'))
pi = j['data']['productInfo']
for d in pi['expertInfo']['datas']:
    print(f"  {d['title'][:50]:50} {d['author']['nickName'][:15]:15} 👍{d['likeCount']}")

# p42461732 真实样例:
#   🌋闯入布罗莫火山:一场极致的冒险之旅          印尼(巴厘岛)全境游玩  👍5
#   7日印度尼西亚攻略😍不看后悔系列❗             旅行小丸子游             👍4
#   7天畅游印度尼西亚🎉跨年旅行必备攻略❗         糖果里的旅行             👍2
#   ...
# 分类 exportType: 1=攻略社区 2=点评
# summary 字段: [{type:0, count:10, title:'全部'}, {type:1, count:6, title:'攻略社区'}, {type:2, count:4, title:'点评'}]
```

**报告用法**:
- 取 `likeCount` 排序前 3 条
- 标题+作者+点赞+`targetLink.appUrl` (ctrip:// 协议深链)
- 章节名: "携程社区 3 篇最热门攻略"

### 2. `PMRecomendInfo.RecommendList[]` — 产品经理 3 个卖点 ⭐⭐⭐

```python
for r in pi['PMRecomendInfo']['RecommendList']:
    print(f"  [{r['RecommendTag']}] {r['DescDetail'][:200]}")
# p42461732 真实样例:
#   [缤纷景点] 精选特色小众且安全玩法,深度探索城市人文...
#   [超值赠送] 应急雨伞+安全专车+定期消毒维护
#   [服务保障] 佩妮达全岛+布罗莫火山日出+Mini越野车+自由活动升级
```

**报告用法**:
- 章节名: "产品经理说"
- 必带 PMPicturesUrl(产品经理照片)

### 3. `imageStyleInfo.poiInfo.ImagePoiList[]` — 9 个 POI 景点 ⭐⭐

```python
for poi in pi['imageStyleInfo']['poiInfo']['ImagePoiList']:
    print(f"  {poi['name']}")
# p42461732 真实样例:
#   爪哇岛, 罗威纳海滩, Twin Lake View, 金塔马尼高地, 水神庙, 圣泉寺, 瓦纳吉里隐山, 德格拉朗梯田
```

**注意**: 字段名是 `name` (不统一,hotelList 叫 `name`,PoiList 也叫 `name`,card 叫 `name` 但常 None)
**报告用法**: 拼接到"行程" 章节,作为"途经 9 大景点"列表

### 4. `brandScore` — 携程自营品牌全维评分 ⭐⭐

```python
bs = pi['brandScore']
# p42461732 真实值:
#   brandName: '携程自营'
#   serviceDestinationName: '印度尼西亚'
#   customersCount: '100000+'
#   customersCountNum: 1895276   # <-- 真实服务人次
#   shopType: 'self'
#   productCategoryList: [11, 26, 34, 42]
```

**报告用法**:
- 章节名: "品牌背书"
- 强信任: "携程自营印尼线已服务 189 万人次"

### 5. `productExtend.MoreRecommendProductList[]` — 8 个同目的地竞品 ⭐⭐⭐

```python
for p in pi['productExtend']['MoreRecommendProductList']:
    print(f"  pid={p['ProductId']} ¥{p['MinPrice']}  {p['ProductName'][:80]}")
# p42461732 真实样例 (8 个布罗莫+伊真+佩妮达产品):
#   pid=66804591 ¥5122  印度尼西亚巴厘岛+泗水+布罗莫火山+佩妮达岛+罗威纳海滩7日6晚私家团
#   pid=69752280 ¥3687  ...7日6晚私家团
#   pid=63638054 ¥4892  ...7日6晚私家团
#   pid=52413261 ¥5462  ...7日5晚私家团
#   pid=72741364 ¥2980  ...7日6晚跟团游 [拼小团/青年小团/1人可拼]  <-- 拼团最便宜!
#   pid=60157594 ¥3837  ...7日6晚私家团 [Youth Tour]
#   pid=73260430 ¥2943  ...7日6晚拼小团 [封顶8人团]  <-- 8人团最便宜!
#   pid=68924817 ¥2999  ...7日6晚跟团游 [拼小团/单人保拼]
```

**报告用法**:
- 章节名: "同类产品比价表"
- 算"差价 = 本产品起价 - 最便宜同类型",告诉用户"专车/管家/私家团溢价"

## 其他被低估的字段(10 个,2026-06-06 增至 10)

### 6. `imageStyleInfo.poiInfo.ImagePoiList[].imgUrl` — 9 张 POI 景点高清图 ⭐⭐

**字段名坑**(2026-06-06 p42461732 实测): 之前猜 `imageList` / `poiName`, **实际是 `imgUrl` + `name`**, 单字段不是数组(每条 POI 1 张图):

```python
for poi in pi['imageStyleInfo']['poiInfo']['ImagePoiList']:
    name = poi.get('name')    # 正确:不是 poiName
    url = poi.get('imgUrl')   # 正确:不是 imageList
    # poiName 是 None,imageList 字段不存在
```

URL pattern: `https://dimg04.c-ctrip.com/images/{id}_C_750_1000.jpg`
下载到本地 → 报告"行程"段插入 9 张图(爪哇岛 / 罗威纳海滩 / Twin Lake View / 金塔马尼高地 / 水神庙 / 圣泉寺 / 瓦纳吉里隐山 / 德格拉朗梯田 / 佩妮达岛)

### 7. `DescriptionInfo.Introduction` — 产品介绍 HTML(含 2 张 banner 图) ⭐⭐

```python
intro = pi['DescriptionInfo']['Introduction']
# 字符串值: "<p><img imageid='41749384' src='https://dimg04.c-ctrip.com/images/0306812000jcuos9l344E.jpg' title='' imageauthorize='...'/><img .../></p>"
```

**报告用法**:
- `re.findall(r'<img[^>]*src="([^"]+)"', intro)` 提所有图
- 提取出的 2 张 banner 图作为报告"产品介绍"段首图

### 8. `expertInfo.datas[].coverImageUrl` — 社区攻略封面图 ⭐

```python
for d in pi['expertInfo']['datas']:
    print(d.get('coverImageUrl'))
# https://dimg04.c-ctrip.com/images/1me0212000jwp2vki4551_W_640_10000_Q90.jpg?proc=source/tripcommunity
```

URL pattern 带 `?proc=source/tripcommunity`(社区专有后缀)。下载作"3 篇最热攻略"章节缩略图。

### 9. `PMRecomendInfo.PMPicturesUrl` — 产品经理照片 ⭐

```python
pmr = pi.get('PMRecomendInfo', {})
print(pmr.get('PMPicturesUrl'))
# https://dimg04.c-ctrip.com/images/30080k000000bs0191724.jpg
```

### 10. `TravelIntroductionInfo.TravelIntroductionList[].TravelOverviewInfo` — 14 个结构化模块 ⭐⭐⭐

**金矿**!`DescriptionInfo.Title/HeadName/SubName` 在 2nd_V3 里没填是常事, 但 **`TravelOverviewInfo.TravelSummaryModuleList[]` 必有数据**:

```python
til = pi['TravelIntroductionInfo']['TravelIntroductionList']
toi = til[0]['TravelOverviewInfo']
for m in toi['TravelSummaryModuleList']:
    if m.get('IsDisplay'):
        print(f"  [{m['ModuleName']}] {m.get('Description', '')}")
# p42461732 真实样例:
#   [住宿] 5晚4钻及以上酒店,1晚3钻及以上酒店
#   [购物] 0购物
#   [团队人数] 不拼团
#   [景点] 20个景点/场馆
#   [餐食] 成人含5早餐1午餐,15次自理
#         儿童含1早餐1午餐,19次自理
#   [服务语言] 普通话
#   [接送机] 提供目的地专车接送机(站/指定点)服务
#   [团友说明] 独立出行,不与陌生人拼团
```

字段:
- `ScenicTimes` 景点数
- `IsNoShopping` 是否 0 购物
- `TravelSummaryModuleList[].IconUrl` 14 个模块图标(住宿/购物/餐食/团队人数/接送机/服务语言/团友说明/自由活动/年龄限制/拼团说明/...)

**报告用法**: 报告"行程亮点"段 4-5 条结构化标签,比 `FeeInfoList` 详细。

### 11. `elderFriendFlag` (bool) — 适老化产品

- p42461732 = True (官方标适合老人,适合带 60+ 父母)
- p64158367 缺(沙巴不一定适老)

### 12. `orderKnow.ContractDesc` (str) — 合同签约方

```
"本产品由上海携程国际旅行社有限公司及具有合法资质的地接社提供相关服务…"
```

**报告用法**: 章节"合同方" 行, 用户维权时知道找谁

### 13. `brandTag` — 品牌标识

```python
pi['brandTag']  # {code:'SiJiaTuan', name:'私家团', linkUrl:..., ImgUrl:{...}}
```

**报告用法**: 顶部徽章 + 跳转链接

### 14. `compositeCoupon` (dict) — 优惠券/促销

- `IsRunSalesPromotion: True` 启用促销
- `promotionList` 优惠券数组
- `promotionDisplayInfoNew.creditInfo` 信用补贴信息(可能含额外 -¥)
- p42461732 真实值: 限时促销 -¥57 + 套餐 -¥492 = 总额外 -¥549

**报告用法**: "可叠加促销" 一行,标"额外省 ¥549"

### 15. `getCommentSummary.comments[]` vs `commentInfo.comments[]` (2026-06-06 更新)

- `commentInfo` 嵌入在 ProductInfo 2nd_V3, 但**总是空数组或字段缺失**
- **真数据走 `getCommentSummary` 独立接口**(用户必须额外查)
- p42461732: getCommentSummary 返回 totalCount=2, scoreAvg=5.0, **comments[] 只 1 条** (接口限制)
- 1 条评论完整字段: userInfo.displayName / content / score / commentTime / subItems[] / tourTypeInfo

### 16. `priceCalendar.scheduleDates[]` vs `dailyMinPrices[]` — 两个价格表

| 字段 | 内容 |
|---|---|
| `scheduleDates` | **10 项采样** (节假日+部分日期) |
| `dailyMinPrices` | **352 天齐全** (全月) |

**报告用法**: 章节"价格日历"用 `dailyMinPrices`;`scheduleDates` 只做参考采样

## 字段缺失模式(被遗忘的"反例" — 字段存在但值为空)

| 字段 | p42461732 | p64158367 | 说明 |
|---|---|---|---|
| `clientInfo` | None | None | (meta 字段,不必管) |
| `productRanking` | None | None | 排名数据(无) |
| `askStatus.AskTitle` | "" | 缺 | 问答(新产品没问答) |
| `userDestinationOrder.productDestinationOrderList` | None | 缺 | 同去过(无) |
| `studyConsultant` | None | 缺 | 留学顾问(不相关) |
| `liveCast` | {} | 缺 | 直播(无) |
| `marketingBanner` | {} | 缺 | 营销 banner(无) |
| `servicePerson` | {} | 缺 | 服务人员(无) |
| `compositeCoupon.promotionList` | [] | 有 | 优惠券池 |
| `SelfPayInfoList` | None | 缺 | 自费项目(并入 FeeInfoList) |
| `DescriptionInfo.Title/HeadName/SubName` | 缺 | 缺 | 产品名, 用 PriceInfo.MinPriceRemark / expertInfo.datas[].productName 拼 |
| `TravelIntroductionInfo.TravelIntroductionList[].Description` | 缺 | 缺 | D1-D7 行程, 走 DOM 文本正则抽 / **改用 TravelOverviewInfo.TravelSummaryModuleList** |
| `TravelIntroductionInfo.TravelIntroductionList[].Name` | 缺 | 缺 | 线路名, 单条线产品永不填 |

## 实战检查清单(报告生成时跑一次)

```python
import json
j = json.load(open('/opt/data/ctrip-data/xhr_graphql_ProductInfo_2nd_V3_h5_<pid>.json'))
pi = j['data']['productInfo']

checks = {
    '品牌背书': pi.get('brandScore', {}).get('customersCountNum'),
    '产品经理 3 卖点': len(pi.get('PMRecomendInfo', {}).get('RecommendList', [])),
    '社区攻略': len(pi.get('expertInfo', {}).get('datas', [])),
    'POI 景点': len(pi.get('imageStyleInfo', {}).get('poiInfo', {}).get('ImagePoiList', [])),
    'POI 图': len([p for p in pi.get('imageStyleInfo', {}).get('poiInfo', {}).get('ImagePoiList', []) if p.get('imgUrl')]),
    'banner 图': pi['DescriptionInfo']['Introduction'].count('<img'),
    'PM 照片': bool(pi.get('PMRecomendInfo', {}).get('PMPicturesUrl')),
    '竞品比价': len(pi.get('productExtend', {}).get('MoreRecommendProductList', [])),
    '结构化模块': len(pi.get('TravelIntroductionInfo', {}).get('TravelIntroductionList', [{}])[0].get('TravelOverviewInfo', {}).get('TravelSummaryModuleList', [])),
    '私家团标识': pi.get('brandTag', {}).get('name'),
    '适老化': pi.get('elderFriendFlag', False),
    '促销优惠': pi.get('compositeCoupon', {}).get('IsRunSalesPromotion', False),
    '价格日历天数': len(pi.get('priceCalendar', {}).get('dailyMinPrices', [])),
}
for k, v in checks.items():
    print(f"  {k:15} {v}")
```

## 图片提取汇总(2026-06-06 p42461732 实测,15/15 全部下载成功)

| 来源 | 字段 | 数量 | URL pattern |
|---|---|---|---|
| 产品介绍 banner | `DescriptionInfo.Introduction` (HTML `<img>`) | 2 | `https://dimg04.c-ctrip.com/images/0305k12000jd92phf989F.jpg` |
| POI 景点 | `imageStyleInfo.poiInfo.ImagePoiList[].imgUrl` | 9 | `https://dimg04.c-ctrip.com/images/{id}_C_750_1000.jpg` |
| 携程社区攻略 | `expertInfo.datas[].coverImageUrl` | 3 | `..._W_640_10000_Q90.jpg?proc=source/tripcommunity` |
| 产品经理推荐 | `PMRecomendInfo.PMPicturesUrl` | 1 | `https://dimg04.c-ctrip.com/images/30080k000000bs0191724.jpg` |
| **总计** | | **15 张** | |

提取脚本: `../ctrip-spa-capture/scripts/extract_images.py`
