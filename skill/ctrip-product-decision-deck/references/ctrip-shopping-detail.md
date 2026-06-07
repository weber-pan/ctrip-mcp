# 携程 getShoppingDetail graphql 抓取 — 完整 4 坑

> 2026-06-07 发现:携程 SPA 不会在普通产品页加载时触发 getShoppingDetail,必须拼 `&shoppingid=32hex` + 用 `expect_response` 同步阻塞。

## 1. 4 大坑(踩过 2 次)

### 坑 1:URL 必须拼 `&shoppingid=32hex`

**现象**:
- 不带 shoppingid 加载 `https://vacations.ctrip.com/travel/detail/p69762187?city=2` → SPA 加载 178 个 req/resp,但 `graphql`/`soa2` 关键字 0 命中
- `page.on('response', ...)` 监听 `getShoppingDetail` 永远 0
- `page.expect_response(lambda r: 'getShoppingDetail' in r.url, timeout=20000)` timeout

**原因**: 携程 SPA 用 shoppingid 作为"询价上下文" key,没这个 key 不发询价 graphql。

**修复**:
```python
url = f'https://vacations.ctrip.com/travel/detail/p{product_id}?city={city_id}&shoppingid={shopping_id}'
```

### 坑 2:`page.on('response')` 不可靠

**现象**: 即使带 shoppingid,`page.on('response', handle)` 仍 0 命中(其他 request/response 正常 178 条)。

**原因**: 携程 SPA 用 `fetch` + `AbortController` 重试机制,response 事件不保证触发。

**修复**: 改用 `page.expect_response` 同步阻塞模式。

### 坑 3:expect_response 一次只能等一个

**现象**: 多个 query 想并发等,但 expect_response 是单次。

**修复**:
```python
for query in ['getShoppingDetail', 'getShoppingPrice']:
    with page.expect_response(lambda r, q=query: q in r.url, timeout=25000) as resp_info:
        page.goto(url, wait_until='domcontentloaded', timeout=30000)
        page.wait_for_timeout(8000)
        page.mouse.wheel(0, 2000)  # 触发滚动加载更多
    body = resp_info.value.text()
    if len(body) > 5000:  # 排除空响应
        saved[query] = json.loads(body)
```

### 坑 4:shoppingid 拿法

**优先级**:
1. 从上次 e2e 抓的 `xhr_ProductInfo_2nd_V3_h5_<pid>.json` 里 `data.productInfo.ShoppingBasic.ShoppingId` 读
2. 用户 URL 里自带的 `?shoppingid=...` 参数
3. Hard-code fallback(已知 32hex)

## 2. 完整工作脚本

```python
from playwright.sync_api import sync_playwright
import json
from pathlib import Path

OUT = Path('/opt/data/ctrip-data')

def get_shopping_id(product_id):
    f = OUT / f'xhr_ProductInfo_2nd_V3_h5_{product_id}.json'
    if f.exists():
        try:
            pi = json.loads(f.read_text())
            sid = (pi.get('data', {}).get('shoppingId')
                  or pi.get('shoppingId')
                  or pi.get('data', {}).get('productInfo', {}).get('ShoppingBasic', {}).get('ShoppingId'))
            if sid and len(sid) == 32:
                return sid
        except: pass
    return '677ec57391474056ab2291eee5c1ca45'

def fetch_with_expect_response(url):
    saved = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            viewport={'width': 1440, 'height': 900},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36'
        )
        page = ctx.new_page()
        for query in ['getShoppingDetail', 'getShoppingPrice']:
            try:
                with page.expect_response(lambda r, q=query: q in r.url, timeout=25000) as resp_info:
                    page.goto(url, wait_until='domcontentloaded', timeout=30000)
                    page.wait_for_timeout(8000)
                    page.mouse.wheel(0, 2000)
                body = resp_info.value.text()
                if len(body) > 5000:
                    key = 'detail' if 'Detail' in query else 'price'
                    saved[key] = json.loads(body)
            except Exception as e:
                print(f'  {query} 失败: {e}')
        browser.close()
    return saved
```

## 3. 关键字段解析样本

```python
# 5 段真实酒店
sd = detail['data']['shoppingDetail']
hotels = sd['Hotel']['Hotels']
for h in hotels:
    b = h['BasicInfo']
    print(f"Seg {h['SegmentNo']}: {b['Name']} (SH={b['Id']}, {b['Star']}星)")

# 真实航班
flights = sd['Flight']['Segments']
for s in flights:
    for f in s['Flights']:
        di = f['DepartInfo']
        ai = f['ArriveInfo']
        print(f"  {f['AirlineInfo']['ShortName']} {f['FlightNo']}: {di['AirportShortName']} → {ai['AirportShortName']} {di['DepartDateTime']}")
```

## 4. 输出文件大小

| 文件 | 大小 | 内容 |
|---|---|---|
| `xhr_getShoppingdetail_<pid>.json` | 188 KB | Hotel.Hotels(5 段) + Flight.Segments(2 段) + Option + productInfo |
| `xhr_getShoppingprice_<pid>.json` | 124 KB | 7 日价格矩阵 |

## 5. 退路(如果 expect_response 仍 timeout)

1. 试加 `args=['--user-data-dir=/tmp/chrome-user']` 复用 cookie
2. 试 `headless=False` 看页面到底有没有渲染(反爬可能让 SPA 不跑)
3. 退到 `imageHotelList` 9 家备选(标红:"间接源,非真实入住")
4. 试 m.ctrip.com 移动端 URL(可能有不同 SPA 路径)
