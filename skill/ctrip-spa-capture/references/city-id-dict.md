# city ID 字典(国内出发城市)

> 验证时间: 2026-06-06  
> 验证数据: p69762187 (DepartureCityPriceList 68 城)

## 规律

`url?city=XX` 不是地区码, 是**携程内部"出发城市 ID"**:

- 1=北京, 2=上海, 3=天津, 5=哈尔滨, 12=南京, 17=杭州, 28=成都, 30=深圳, 32=广州
- 1244=重庆
- 拼音字母排序 + 行政区划

**68 个城市**(携程支持的所有国内出发地), 不含海外。

## 部分字典(常用 20 个)

| ID | 城市 | 拼音 | 拼音头 |
|---|---|---|---|
| 1 | 北京 | Beijing | B |
| 2 | **上海** | Shanghai | S |
| 3 | 天津 | Tianjin | T |
| 5 | 哈尔滨 | Haerbin | H |
| 12 | 南京 | Nanjing | N |
| 17 | 杭州 | Hangzhou | H |
| 28 | 成都 | Chengdu | C |
| 30 | 深圳 | Shenzhen | S |
| 32 | 广州 | Guangzhou | G |
| 1244 | 重庆 | Chongqing | C |

## 完整字典获取

抓取后从 `PriceInfo.DepartureCityPriceList[]` 拿:

```python
import json
j = json.load(open('/opt/data/ctrip-data/xhr_graphql_ProductInfo_2nd_V3_h5.json'))
dpl = j['data']['productInfo']['PriceInfo']['DepartureCityPriceList']
# 68 项, 每项: {DepartureCityId, DepartureCityName, MinPrice, DisplayPrice, ...}
```

## 任意城市 3 种方式

1. **URL 改 `city=XX`**(数字) - 已知 ID 时
2. **脚本加 `--city-id` 参数** - 写脚本
3. **从 DepartureCityPriceList 找** - 抓取后查
