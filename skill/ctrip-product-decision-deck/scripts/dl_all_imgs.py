#!/usr/bin/env python3
"""全量下载携程产品图 — hotel + comment + competitor + ranking 4 类
   (extract_images.py 只抓 desc+poi+expert+pm 4 类,漏 45+ 张)

用法: /opt/data/.venv/bin/python /opt/data/scripts/ctrip_download_all_images.py <product_id>
例:   /opt/data/.venv/bin/python /opt/data/scripts/ctrip_download_all_images.py 69762187
"""
import json, os, sys, urllib.request
from pathlib import Path

if len(sys.argv) < 2:
    print("用法: dl_all_imgs.py <product_id>")
    sys.exit(1)
PID = sys.argv[1]

DATA = Path('/opt/data/ctrip-data')
OUT = DATA / f'img_{PID}'
OUT.mkdir(exist_ok=True)
JSON_PATH = DATA / f'xhr_ProductInfo_2nd_V3_h5_{PID}.json'

if not JSON_PATH.exists():
    print(f"ERR {JSON_PATH} 不存在,先跑 ctrip-spa-capture 抓接口")
    sys.exit(1)

with open(JSON_PATH) as f:
    pi = json.load(f)['data']['productInfo']

def dl(url, local):
    try:
        if local.exists() and local.stat().st_size > 1000:
            return f"skip({local.stat().st_size//1024}KB)"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://m.ctrip.com/'})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
        local.write_bytes(data)
        return f"ok({len(data)//1024}KB)"
    except Exception as e:
        return f"FAIL({e})"

total, ok = 0, 0

# 1) HOTEL
print("=== HOTEL ===")
for i, h in enumerate(pi['imageStyleInfo']['hotelInfo']['imageHotelList']):
    name = h.get('name', f'hotel_{i}').replace('/', '_')
    for j, img in enumerate(h.get('imageList', [])):
        url = img.get('imgUrl', '')
        if not url: continue
        ext = 'png' if '.png' in url else 'jpg'
        local = OUT / f"hotel_{i}_{name}_{j}.{ext}"
        r = dl(url, local)
        print(f"  [{i}][{j}] {name} {r}")
        total += 1
        if r.startswith(('ok', 'skip')): ok += 1

# 2) COMMENT
print("\n=== COMMENT ===")
for i, c in enumerate(pi['commentInfo']['comments']):
    atts = c.get('attachments', [])
    if isinstance(atts, str): atts = json.loads(atts)
    for j, a in enumerate(atts):
        url = a.get('url', '') if isinstance(a, dict) else ''
        if not url: continue
        ext = 'png' if '.png' in url else 'jpg'
        local = OUT / f"comment_{i}_{j}.{ext}"
        r = dl(url, local)
        print(f"  comment[{i}][{j}] {r}")
        total += 1
        if r.startswith(('ok', 'skip')): ok += 1

# 3) COMPETITOR
print("\n=== COMPETITOR ===")
for i, p in enumerate(pi['productExtend']['MoreRecommendProductList']):
    url = p.get('ImageUrl', '')
    if not url: continue
    ext = 'png' if '.png' in url else 'jpg'
    pid = p.get('ProductId', i)
    local = OUT / f"competitor_{i}_{pid}.{ext}"
    r = dl(url, local)
    print(f"  competitor[{i}] {r}")
    total += 1
    if r.startswith(('ok', 'skip')): ok += 1

# 4) RANKING (dedup)
print("\n=== RANKING ===")
seen = set()
def walk(obj):
    cnt = 0
    if isinstance(obj, dict):
        if 'GlobalRankingInfo' in obj and isinstance(obj['GlobalRankingInfo'], dict):
            url = obj['GlobalRankingInfo'].get('ImageUrl')
            if url and url not in seen:
                seen.add(url)
                idx = len(seen)
                local = OUT / f"ranking_{idx}.jpg"
                r = dl(url, local)
                print(f"  ranking[{idx}] {r}")
                return 1
        for v in obj.values():
            cnt += walk(v)
    elif isinstance(obj, list):
        for x in obj:
            cnt += walk(x)
    return cnt

n_rank = walk(pi)
total += n_rank
ok += n_rank

print(f"\n=== Total: {ok}/{total} ===")
print(f"=== {len(list(OUT.glob('*')))} files in {OUT} ===")
