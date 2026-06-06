"""test ctrip-mcp end-to-end: 实际抓产品 64158367"""
import sys, asyncio, json
sys.path.insert(0, '/opt/data/ctrip-mcp/src')

from ctrip_mcp.server import call_tool

async def main():
    print("=== 1) ctrip_spa_capture ===")
    r1 = await call_tool("ctrip_spa_capture", {
        "product_id": 64158367,
        "depart_city_id": 2,
        "scroll": True,
    })
    data1 = json.loads(r1[0].text)
    print(f"duration: {data1['duration_s']}s")
    print(f"xhrs count: {len(data1['xhrs'])}")
    for tag, path in data1['saved'].items():
        print(f"  saved {tag}: {path}")

    print("\n=== 2) ctrip_get_product ===")
    r2 = await call_tool("ctrip_get_product", {"product_id": 64158367})
    d = json.loads(r2[0].text)
    if "❌" in r2[0].text or "错误" in r2[0].text:
        print("ERROR:")
        print(r2[0].text[:2000])
        return
    pb = d['product_basic']
    print(f"  name: {pb['name']}")
    print(f"  days_nights: {pb['days_nights']}")
    print(f"  min_price: ¥{pb['min_price']} (orig ¥{pb['origin_price']}) on {pb['min_price_date']}")
    print(f"  remark: {pb['remark'][:200]}...")
    print(f"  lines: {len(d['lines'])}")
    for ln in d['lines']:
        print(f"    - subId={ln['subProductId']} sort={ln.get('sortNumber','?')} {ln['name']}")
    print(f"  hotels: {len(d['hotels'])}")
    for h in d['hotels'][:3]:
        print(f"    - {h['hotelId']} {h['name']}")
    print(f"  comments: scoreAvg={d['comments'].get('scoreAvg')} count={d['comments'].get('totalCount')}")
    print(f"  price_calendar dates: {len(d['price_calendar']['dates'])}")
    if d['price_calendar']['min_price_overall']:
        m = d['price_calendar']['min_price_overall']
        print(f"    全月最低: {m['date']} ¥{m['price']} (line {m['lineName']})")
    print(f"  fee_summary: {len(d['fee_summary'])}")
    print(f"  visa_summary: {len(d['visa_summary'])}")
    print(f"  more_recommend: {len(d['more_recommend'])}")

    print("\n=== 3) 7/4 班期价 (4 条线) ===")
    by_date = d['price_calendar']['by_date']
    if '2026-07-04' in by_date:
        for p in by_date['2026-07-04']:
            print(f"  subId={p['productId']}  ¥{p['price']}  {p['lineName']}")
    else:
        print(f"  7/4 不在班期表! 找到的日期范围: {min(by_date.keys())} ~ {max(by_date.keys())}")
        # 取离 7/4 最近的
        import bisect
        keys = sorted(by_date.keys())
        target = '2026-07-04'
        i = bisect.bisect_left(keys, target)
        for j in [i-1, i, i+1]:
            if 0 <= j < len(keys):
                print(f"  邻近 {keys[j]}: {by_date[keys[j]]}")

asyncio.run(main())
