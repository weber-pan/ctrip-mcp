#!/usr/bin/env python3
"""make_map_leaflet.py v4 — 修复 day/坐标/中文标签"""
import sys, json, subprocess
from pathlib import Path
from collections import defaultdict

DATA = Path('/opt/data/ctrip-data')

# 坐标字典 (补齐 爪哇岛/Kapas Biru)
GEO = {
    '泗水':(112.7508,-7.2575),'玛琅':(112.6304,-7.9666),
    '布罗莫火山':(112.9534,-7.9425),'伊真火山':(114.2430,-8.0580),
    'Ijen':(114.2430,-8.0580),'Bromo':(112.9534,-7.9425),
    'Kanigaran':(113.2150,-7.7540),'Probolinggo':(113.2150,-7.7540),
    'Licin':(114.2200,-8.1830),
    'Surabaya':(112.7508,-7.2575),'Malang':(112.6304,-7.9666),
    '罗威纳海滩':(115.0260,-8.1750),'Lovina':(115.0260,-8.1750),
    '水神庙':(115.2790,-8.2818),'百度库':(115.2790,-8.2818),
    '金塔马尼':(115.2790,-8.3580),'金塔马尼高地':(115.2790,-8.3580),'京打马尼':(115.2790,-8.3580),
    '双子湖':(115.4050,-8.2500),
    '德格拉朗梯田':(115.2770,-8.4270),'Tegalalang':(115.2770,-8.4270),
    '乌布':(115.2625,-8.5069),'Ubud':(115.2625,-8.5069),
    '佩妮达岛':(115.4500,-8.7333),'Nusa Penida':(115.4500,-8.7333),
    '巴厘岛':(115.0920,-8.4095),'巴厘岛机场':(115.1670,-8.7482),'DPS':(115.1670,-8.7482),
    'Bali':(115.0920,-8.4095),
    # 补齐
    '爪哇岛':(113.0,-7.5),  # Java 岛中心
    'Kapas Biru Waterfall':(114.02,-8.17),  # 伊真附近瀑布
}
DEP = {'上海','北京','广州','深圳','成都','杭州','南京','重庆','西安','昆明','上海浦东','虹桥','上海虹桥','上海浦东机场'}

def geo(n):
    if n in GEO: return GEO[n]
    for k,v in GEO.items():
        if k in n or n in k: return v

def main():
    pid = sys.argv[1]
    j2 = jv = None
    f2 = DATA/'xhr_graphql_ProductInfo_2nd_V3_h5.json'
    fv = DATA/'xhr_graphql_VPC_SelectDateProductInfo_h5.json'
    if f2.exists(): j2 = json.loads(f2.read_text())
    if fv.exists(): jv = json.loads(fv.read_text())
    j2 = j2 or {}; jv = jv or {}
    pi2 = j2.get('data',{}).get('productInfo',{})
    piv = jv.get('data',{}).get('productInfo',{})
    title = piv.get('BasicInfo',{}).get('Title') or pi2.get('Title') or '产品'

    # === POI ===
    poi, seen = [], set()
    isi = pi2.get('imageStyleInfo',{})
    for obj in isi.get('poiInfo',{}).get('ImagePoiList',[]):
        n = obj.get('name',''); g = geo(n); d = obj.get('day') or 4
        if n in DEP or not g: continue
        k = f"{n}_{g[0]:.1f}"
        if k not in seen: seen.add(k); poi.append({'name':n,'value':list(g),'day':d,'hotel':False})
    # 酒店 — day 从 VPC 行程推断 (不能得 0 就免, 挂 D1)
    hotel_day = {1}  # 默认泗水酒店 D1
    for h in isi.get('hotelInfo',{}).get('imageHotelList',[]):
        n = h.get('name',''); g = geo(n)
        if not g: continue
        k = f"{n}_{g[0]:.1f}"
        if k not in seen: seen.add(k); poi.append({'name':n,'value':list(g),'day':1,'hotel':True})
    # 林塘露库帐篷度假村-伊真 -> 伊真 day=4
    for p in poi:
        if '伊真' in p['name'] or 'Ijen' in p['name']:
            p['day'] = 4

    # 按地理顺序连线 (Lat 从北到南 ≈ 从上海到巴厘)
    # 先用原始 day 排序, 同 day 按 day 内部, 不同 day = 跨天
    ps = sorted(poi, key=lambda p: (p.get('day',1), p['value'][1]))  # lat 从北到南
    
    # 按 day 分组
    bd = defaultdict(list)
    for p in ps: bd[p.get('day',1)].append(p)
    
    routes, dp = [], []
    prev = None
    
    for d in sorted(bd.keys()):
        pts = bd[d]
        # 每个 day 取代表性 POI (非酒店优先)
        rep = None
        for p in pts:
            if not p['hotel']:
                rep = p
                break
        if rep is None:
            rep = pts[0]
        
        # 跨天连线 (prev → rep)
        if prev and 'value' in prev and 'value' in rep:
            routes.append({
                'coords': [prev['value'], rep['value']],
                'day': f"D{d}",
                'transport': 'ground'
            })
        prev = rep
        
        # day panel: 显示当天景点
        names = [p['name'] for p in pts if not p['hotel']]
        if not names:
            names = [pts[0]['name']]
        dp.append(f'<div class="row"><b style="color:#409eff">D{d}</b> {" · ".join(names[:3])}</div>')

    tshort = title[:30]+('...' if len(title)>30 else '')
    dp_html = '\n'.join(dp) or '暂无行程'

    html = f'''<!DOCTYPE html>
<html><head>
<meta charset="utf-8"><title>{tshort} · 路线</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<style>
* {{margin:0;padding:0;box-sizing:border-box}}
body {{font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;background:#000}}
#map {{width:100%;height:100vh}}
.info {{position:absolute;top:20px;right:20px;z-index:1000;background:rgba(255,255,255,0.95);border-radius:8px;padding:14px 18px;max-width:280px;box-shadow:0 4px 16px rgba(0,0,0,0.2);font-size:13px;color:#606266;line-height:1.7}}
.info h3 {{font-size:14px;color:#303133;margin-bottom:8px;border-bottom:1px solid #eee;padding-bottom:6px}}
.info .row {{margin:2px 0}}
.legend {{position:absolute;bottom:20px;left:20px;z-index:1000;background:rgba(255,255,255,0.92);border-radius:8px;padding:10px 14px;font-size:12px;box-shadow:0 2px 8px rgba(0,0,0,0.1)}}
.l-item {{display:flex;align-items:center;gap:6px;margin:2px 0}}
.dot12 {{width:12px;height:12px;border-radius:50%}}
.lin3 {{width:22px;height:3px;border-radius:2px;display:inline-block}}
.dlabel {{background:#409eff;color:#fff;padding:1px 7px;border-radius:4px;font-size:11px;font-weight:700;white-space:nowrap;line-height:18px;text-align:center}}
.dlabel.flight {{background:#f56c6c}}
.poilabel {{font-size:11px;font-weight:500;color:#333;background:rgba(255,255,255,0.85);padding:1px 5px;border-radius:3px;white-space:nowrap;border:1px solid rgba(0,0,0,0.1);line-height:16px}}
</style>
</head><body>
<div id="map"></div>
<div class="info"><h3>{tshort}</h3>{dp_html}</div>
<div class="legend">
<div class="l-item"><div class="dot12" style="background:#67c23a"></div>景点</div>
<div class="l-item"><div class="dot12" style="background:#e6a23c"></div>住宿</div>
<div class="l-item"><div class="lin3" style="background:#409eff"></div>地面路线</div>
</div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
var map = L.map('map',{{zoomControl:true}});
// ESRI 全球卫星图
L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}',{{maxZoom:19,attribution:''}}).addTo(map);

var poi = {json.dumps(poi, ensure_ascii=False)};
var routes = {json.dumps(routes, ensure_ascii=False)};

var all = [];
poi.forEach(p=>all.push(p.value));
routes.forEach(r=>r.coords.forEach(c=>all.push(c)));
if(all.length) map.fitBounds(L.latLngBounds(all.map(c=>[c[1],c[0]])),{{padding:[60,60]}});

poi.forEach(p=>{{
  var col = p.hotel?'#e6a23c':'#67c23a';
  var m = L.circleMarker([p.value[1],p.value[0]],{{radius:p.hotel?10:8,fillColor:col,color:'#fff',weight:2,fillOpacity:p.hotel?0.8:0.9}}).addTo(map);
  m.bindPopup('<b>'+p.name+'</b> D'+p.day+(p.hotel?' · 住宿':''));
  // 中文标签 (POI 名称直接显示)
  L.marker([p.value[1],p.value[0]],{{
    icon:L.divIcon({{className:'poilabel',html:p.name,iconSize:[0,0],iconAnchor:[0,-12]}})
  }}).addTo(map);
}});

routes.forEach(r=>{{
  var ll=r.coords.map(c=>[c[1],c[0]]);
  L.polyline(ll,{{color:'#409eff',weight:3,opacity:0.85}}).addTo(map);
  var mid=ll[Math.floor(ll.length/2)];
  L.marker(mid,{{icon:L.divIcon({{className:'dlabel',html:r.day,iconSize:[34,20],iconAnchor:[17,10]}})}}).addTo(map);
}});
</script>
</body></html>'''

    out = DATA / f'map_leaflet_{pid}.html'
    out.write_text(html)
    print(f"OK: {out} POI:{len(poi)} 路线:{len(routes)} 日:{sorted(bd.keys())}")

    png = DATA / f'map_leaflet_{pid}.png'
    subprocess.run(['/opt/hermes/.venv/bin/python','/opt/data/skills/devops/ctrip-spa-capture/scripts/snapshot_html.py',
        f'http://localhost:8799/map_leaflet_{pid}.html', str(png), '1600','1000','6000','10000'], timeout=60)

if __name__ == '__main__':
    main()
