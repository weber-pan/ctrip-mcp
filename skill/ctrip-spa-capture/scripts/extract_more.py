#!/usr/bin/env python3
"""
extract_more.py — 从已抓的 xhr JSON 提取"被遗忘"字段
- 价格日历 CSV (VPC 接口 207 天)
- 4 类图片 (DescriptionInfo/POI/PM/brandTag)
- 7 大类摘要 (cardItems)
- 行程 10 段 (SegmentInfo)
- 9 家可选酒店 (imageHotelList)
- 13 目的地 (Destinations)
- 68 城市价 (DepartureCityPriceList)
- 销量/流量 (OrderPersonCount/VacationPersons)
- 点评 (getCommentSummary)

用法:
  python3 extract_more.py <product_id>
  # 输出目录: /opt/data/ctrip-data/
"""
import sys
import os
import json
import re
import csv
import subprocess
from pathlib import Path
from collections import defaultdict

DATA_DIR = Path('/opt/data/ctrip-data')


def load_xhr(pattern):
    """按 glob 找 xhr 文件并加载 JSON"""
    files = list(DATA_DIR.glob(pattern))
    if not files:
        return None, None
    # 取最新
    fn = max(files, key=lambda p: p.stat().st_mtime)
    try:
        with open(fn) as f:
            return json.load(f), fn
    except Exception as e:
        print(f"  [warn] 加载 {fn} 失败: {e}")
        return None, fn


def extract_price_calendar(product_id, dmp):
    """价格日历落盘 CSV"""
    out = DATA_DIR / f"price_calendar_{product_id}.csv"
    with open(out, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['date', 'price', 'display_price', 'inventory', 'original_price', 'realtime', 'sub_product_count', 'sub_products'])
        for d in dmp:
            orig = d.get('originalPriceInfo', {}).get('originalPrice', '')
            sub_p = d.get('productPrices', [])
            sub_ids = '|'.join(str(p.get('productId', '')) for p in sub_p)
            w.writerow([
                d.get('date', ''),
                d.get('price', ''),
                d.get('displayPrice', ''),
                d.get('inventory', ''),
                orig,
                d.get('realtime', ''),
                len(sub_p),
                sub_ids,
            ])
    return out, len(dmp)


def extract_images(product_id, pi, ei, pmr, bt):
    """4 类图片源 + 1 类 brand"""
    out_dir = DATA_DIR / f"img_{product_id}"
    out_dir.mkdir(exist_ok=True)
    count = 0
    manifest = []

    # 1) DescriptionInfo.Introduction
    intro = pi.get('DescriptionInfo', {}).get('Introduction', '')
    for i, u in enumerate(re.findall(r'<img[^>]*src="([^"]+)"', intro)):
        fn = out_dir / f"desc_{i}.jpg"
        subprocess.run(['curl', '-sL', '-o', str(fn), u], check=False)
        sz = fn.stat().st_size if fn.exists() else 0
        if sz > 1000:
            manifest.append({'type': 'description', 'url': u, 'file': str(fn), 'size': sz})
            count += 1

    # 2) POI
    for p in pi.get('imageStyleInfo', {}).get('poiInfo', {}).get('ImagePoiList', []):
        u = p.get('imgUrl')
        if not u: continue
        name = re.sub(r'[^\w]', '_', p.get('name', 'poi'))[:50]
        fn = out_dir / f"poi_{name}.jpg"
        subprocess.run(['curl', '-sL', '-o', str(fn), u], check=False)
        sz = fn.stat().st_size if fn.exists() else 0
        if sz > 1000:
            manifest.append({'type': 'poi', 'name': p.get('name'), 'poiId': p.get('poiId'), 'url': u, 'file': str(fn), 'size': sz})
            count += 1

    # 3) expertInfo 攻略封面
    for d in ei.get('datas', []):
        u = d.get('coverImageUrl')
        if not u: continue
        title = re.sub(r'[^\w]', '_', d.get('title', 'expert'))[:50]
        fn = out_dir / f"expert_{title}.jpg"
        subprocess.run(['curl', '-sL', '-o', str(fn), u], check=False)
        sz = fn.stat().st_size if fn.exists() else 0
        if sz > 1000:
            manifest.append({'type': 'expert', 'title': d.get('title'), 'url': u, 'file': str(fn), 'size': sz})
            count += 1

    # 4) PMRecomendInfo
    pm = pmr.get('PMPicturesUrl')
    if pm:
        fn = out_dir / "pm.jpg"
        subprocess.run(['curl', '-sL', '-o', str(fn), pm], check=False)
        sz = fn.stat().st_size if fn.exists() else 0
        if sz > 1000:
            manifest.append({'type': 'pm', 'url': pm, 'file': str(fn), 'size': sz})
            count += 1

    # 5) brandTag
    for k, v in (bt.get('ImgUrl') or {}).items():
        if not v: continue
        fn = out_dir / f"brand_{k}.png"
        subprocess.run(['curl', '-sL', '-o', str(fn), v], check=False)
        sz = fn.stat().st_size if fn.exists() else 0
        if sz > 1000:
            manifest.append({'type': 'brand', 'role': k, 'url': v, 'file': str(fn), 'size': sz})
            count += 1

    # 落盘 manifest
    with open(out_dir / "manifest.json", 'w') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    return out_dir, count, manifest


def main():
    if len(sys.argv) < 2:
        print("用法: extract_more.py <product_id>")
        sys.exit(1)
    product_id = sys.argv[1]
    print(f"=== extract_more.py product_id={product_id} ===\n")

    # 加载 2nd_V3 — 文件名无 _pid 后缀, 取最新 .json
    files_2nd = [f for f in DATA_DIR.glob("xhr_graphql_ProductInfo_2nd_V3_h5*.json")
                 if f.is_file()]
    j2, fn2 = (None, None)
    if files_2nd:
        fn2 = max(files_2nd, key=lambda p: p.stat().st_mtime)
        try:
            with open(fn2) as f:
                j2 = json.load(f)
        except Exception as e:
            print(f"  [warn] 加载 {fn2} 失败: {e}")
    if not j2:
        print("  ❌ 2nd_V3 没找到, 请先跑 ctrip_spa_capture.py")
        sys.exit(1)
    pi = j2['data']['productInfo']
    print(f"  2nd_V3: {fn2.name}")

    # 加载 VPC — 文件名无 _pid 后缀
    files_vpc = [f for f in DATA_DIR.glob("xhr_graphql_VPC_SelectDateProductInfo_h5*.json")
                 if f.is_file()]
    jv, fnv = (None, None)
    if files_vpc:
        fnv = max(files_vpc, key=lambda p: p.stat().st_mtime)
        try:
            with open(fnv) as f:
                jv = json.load(f)
        except Exception:
            pass
    piv = jv['data']['productInfo'] if jv else {}
    if jv:
        print(f"  VPC: {fnv.name}")
    else:
        print(f"  [warn] VPC 没找到, 行程/销量字段跳过")

    # 1) 价格日历
    print(f"\n--- 1) 价格日历 ---")
    dmp = piv.get('priceCalendar', {}).get('dailyMinPrices', [])
    if dmp:
        csv_path, n = extract_price_calendar(product_id, dmp)
        print(f"  落盘 {csv_path} {n} 天")
        by_month = defaultdict(int)
        prices_by_month = defaultdict(list)
        for d in dmp:
            ym = str(d.get('date', ''))[:7]
            by_month[ym] += 1
            p = d.get('price', 0)
            if p: prices_by_month[ym].append(p)
        print(f"  按月:")
        for ym in sorted(by_month.keys()):
            plist = prices_by_month[ym]
            if plist:
                print(f"    {ym}: {by_month[ym]:3d} 天, ¥{min(plist)}~{max(plist)} 均 ¥{sum(plist)//len(plist)}")

    # 2) 图片
    print(f"\n--- 2) 图片提取 ---")
    ei = pi.get('expertInfo', {})
    pmr = pi.get('PMRecomendInfo', {})
    bt = pi.get('brandTag', {})
    img_dir, n_imgs, manifest = extract_images(product_id, pi, ei, pmr, bt)
    print(f"  落盘 {img_dir} {n_imgs} 张图")
    for m in manifest[:10]:
        print(f"    [{m['type']}] {m['file'].split('/')[-1]} ({m['size']//1024} KB)")

    # 3) 7 段摘要 (cardItems)
    print(f"\n--- 3) 7 段摘要 (cardItems) ---")
    c0 = pi.get('groupCard', {}).get('cards', [{}])[0]
    for ci in c0.get('cardItems', []):
        g = ci.get('groupName', '?')
        c = ci.get('displayContent', '?')
        print(f"  {g}: {c}")

    # 4) 行程 10 段
    print(f"\n--- 4) 行程结构 (SegmentInfo) ---")
    si = piv.get('SegmentInfo', {})
    segs = si.get('Segments', [])
    for i, s in enumerate(segs, 1):
        flight = '✈️' if s.get('IsFlight') else '🚐'
        hotel = f" {s.get('MinStayDays', 0)} 晚" if s.get('IsIncludeHotel') else ''
        print(f"  [{i}] {flight} {s.get('DepartureCityName')}→{s.get('DestinationCityName')}{hotel}")

    # 5) 9 家可选酒店
    print(f"\n--- 5) 可选酒店 (imageHotelList) ---")
    h_list = pi.get('imageStyleInfo', {}).get('hotelInfo', {}).get('imageHotelList', [])
    print(f"  {len(h_list)} 家:")
    for h in h_list:
        print(f"    {h.get('name', '?')[:25]:25} ★{h.get('star')} ⭐{h.get('score')} id={h.get('hotelId')}  {h.get('award', '')[:30]}")

    # 6) 13 目的地
    print(f"\n--- 6) 目的地 (Destinations) ---")
    bi = piv.get('BasicInfo', {})
    dests = bi.get('Destinations', [])
    by_type = defaultdict(int)
    for d in dests:
        by_type[d.get('Type', '?')] += 1
    print(f"  {len(dests)} 项 (国={by_type.get(1, 0)} 省={by_type.get(2, 0)} 城={by_type.get(3, 0)})")

    # 7) 68 城价
    print(f"\n--- 7) 出发城市价 (DepartureCityPriceList) ---")
    dpl = pi.get('PriceInfo', {}).get('DepartureCityPriceList', [])
    print(f"  {len(dpl)} 城")
    sh = next((d for d in dpl if d.get('DepartureCityId') == 2), None)
    if sh:
        print(f"  上海(id=2): ¥{sh.get('MinPrice')}")
    # 最低/最高
    prices = [(d.get('DepartureCityName'), d.get('MinPrice')) for d in dpl if d.get('MinPrice')]
    if prices:
        prices.sort(key=lambda x: x[1])
        print(f"  最便宜: {prices[0][0]} ¥{prices[0][1]}")
        print(f"  最贵:   {prices[-1][0]} ¥{prices[-1][1]}")

    # 8) 销量/流量
    print(f"\n--- 8) 销量/流量 ---")
    print(f"  OrderPersonCount={bi.get('OrderPersonCount')} (总销量)")
    print(f"  PersonsMonth={bi.get('PersonsMonth')} (本月销量)")
    vp = bi.get('VacationPersons', {})
    print(f"  VisitsMonth={vp.get('VisitsMonth')} VisitsWeek={vp.get('VisitsWeek')}")
    print(f"  ConsultsMonth={vp.get('ConsultsMonth')} ConsultsWeek={vp.get('ConsultsWeek')}")

    # 9) 点评
    print(f"\n--- 9) 点评 ---")
    gc, fng = load_xhr(f"xhr_getCommentSummary*.json")
    if gc:
        score = gc.get('score') or '?'
        count = gc.get('count') or gc.get('totalCount') or '?'
        print(f"  评分 {score} / 点评数 {count}")
        for c in gc.get('comments', [])[:3]:
            u = c.get('userInfo', {}).get('displayName', '?')
            txt = c.get('content', '?')[:120]
            print(f"    {u}: {txt}")

    # 10) 巴厘岛旅游税等特殊费用
    print(f"\n--- 10) 特殊费用 ---")
    for fee in pi.get('FeeInfoList', []):
        cat = fee.get('Category', '?')
        for cl in fee.get('ProductClauseList', []):
            for sub in cl.get('ClauseSubItemList', []):
                for tp in sub.get('TargetPopulationItemList', []):
                    d = tp.get('Description', '')
                    if any(kw in d for kw in ['印尼盾', '美金', '落地签', '旅游税']):
                        print(f"  [{cat}] {d[:200]}")

    # 11) 竞品
    print(f"\n--- 11) 竞品 (MoreRecommendProductList) ---")
    ml = pi.get('productExtend', {}).get('MoreRecommendProductList', [])
    for p in ml:
        name = p.get('ProductName', '?')[:60]
        pid = p.get('ProductId') or p.get('Id', '?')
        price = p.get('MinPrice', '?')
        print(f"  ¥{price:>5}  pid={pid}  {name}")

    print(f"\n✅ 全部字段提取完成")


if __name__ == '__main__':
    main()
