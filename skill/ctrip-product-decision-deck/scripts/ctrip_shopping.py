#!/usr/bin/env python3
"""
ctrip_shopping.py — 抓 shoppingid + getShoppingDetail + getShoppingPrice
- 2026-06-07 新:e2e 6 个 xhr json 没拿全 5 段真实酒店 + 真实航班班次
- 这两个在另一个 graphql 接口 getShoppingDetail 里,由 shoppingid 触发
- 关键:URL 必须带 shoppingid 参数,SPA 才会触发 graphql 查询

用法:
  /opt/data/.venv/bin/python scripts/ctrip_shopping.py <productId> <cityId>

产物:
  /opt/data/ctrip-data/xhr_getShoppingdetail_<pid>.json  (~110 KB · 5 段酒店 + 航班)
  /opt/data/ctrip-data/xhr_getShoppingprice_<pid>.json   (~150 KB · 7 日价格)

关键字段:
  data.shoppingDetail.Hotel.Hotels[].BasicInfo.Id    = 携程 SH ID (5 家真实酒店)
  data.shoppingDetail.Hotel.Hotels[].BasicInfo.Name  = 酒店名
  data.shoppingDetail.Flight.Segments[].Flights[]    = 真实航司班次 (GA895/G326/...)
"""
import sys, json
from playwright.sync_api import sync_playwright
from pathlib import Path

OUT = Path('/opt/data/ctrip-data')

def get_shopping_id(product_id: str) -> str:
    """从 e2e json 拿 shoppingid,失败回退到上次的"""
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
    return '677ec57391474056ab2291eee5c1ca45'  # fallback

def fetch_with_expect_response(url: str) -> dict:
    """用 expect_response 模式抓 getShoppingDetail + getShoppingPrice"""
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
                    try:
                        saved[key] = json.loads(body)
                        print(f'  [+] 抓 {key}: {len(body)} 字节')
                    except Exception as e:
                        print(f'    parse err: {e}')
                # 重新加载以触发下一个
                page.wait_for_timeout(2000)
            except Exception as e:
                print(f'    {query} 抓取失败: {str(e)[:80]}')
        browser.close()
    return saved

def main():
    product_id = sys.argv[1] if len(sys.argv) > 1 else '69762187'
    city_id = sys.argv[2] if len(sys.argv) > 2 else '2'
    shopping_id = get_shopping_id(product_id)
    url = f'https://vacations.ctrip.com/travel/detail/p{product_id}?city={city_id}&shoppingid={shopping_id}'
    print(f'[use] shoppingid={shopping_id}')

    saved = fetch_with_expect_response(url)

    ok = 0
    for k, v in saved.items():
        fn = OUT / f'xhr_getShopping{k}_{product_id}.json'
        fn.write_text(json.dumps(v, ensure_ascii=False, indent=2))
        print(f'  保存 {fn}: {fn.stat().st_size} 字节')
        ok += 1

    if ok < 2:
        print(f'\n[!] 只抓到 {ok}/2 个')
        sys.exit(1)

    # 解析摘要
    d = saved.get('detail')
    if d and 'data' in d and 'shoppingDetail' in d['data']:
        sd = d['data']['shoppingDetail']
        hotels = sd.get('Hotel', {}).get('Hotels', [])
        flights = sd.get('Flight', {}).get('Segments', [])
        print(f'\n[摘要]')
        print(f'  shoppingId: {sd.get("shoppingId")}')
        print(f'  Hotel: {len(hotels)} 段')
        for h in hotels:
            b = h.get('BasicInfo', {})
            print(f'    Seg {h.get("SegmentNo")}: {b.get("Name")} (SH={b.get("Id")}, {b.get("Star")}星)')
        print(f'  Flight: {len(flights)} 段 (去+回)')
        for s in flights:
            for f in s.get('Flights', []):
                di = f.get('DepartInfo', {})
                ai = f.get('ArriveInfo', {})
                print(f'    {f.get("AirlineInfo", {}).get("ShortName")} {f.get("FlightNo")}: {di.get("AirportShortName")} → {ai.get("AirportShortName")}')

if __name__ == '__main__':
    main()
