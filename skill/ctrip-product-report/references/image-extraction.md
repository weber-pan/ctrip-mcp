# 携程 SPA 4 类图片源提取指南

> 2026-06-06 p42461732 实测: 一次抓取拿到 15 张图, 全部下载成功 (121KB-1.2MB)

## 4 类源 + 字段路径 + 真实案例

### 1. 产品介绍 banner (2 张)

**字段**: `DescriptionInfo.Introduction` (HTML 字符串)

```html
<p><img imageid="41749384" src="https://dimg04.c-ctrip.com/images/0306812000jcuos9l344E.jpg" title="" imageauthorize="41749384图片有效-有效期"/></p>
```

**提取**:
```python
import re
intro = pi["DescriptionInfo"]["Introduction"]
for u in re.findall(r'<img[^>]*src="([^"]+)"', intro):
    all_imgs.append(("desc", u))
# imageid 也在: re.findall(r'imageid="(\d+)"', intro) → ["41749384", "41751250"]
```

**注意**: 字段值可能是空字符串 `""`, 不要先 `if Introduction:` 才解析, **直接 parse HTML**。

### 2. POI 景点图 (9 张, **字段名坑**)

**字段**: `imageStyleInfo.poiInfo.ImagePoiList[]` (list, 不是 dict)

**单条结构**:
```json
{
  "poiId": 142364940,
  "name": "爪哇岛",          ← 不是 "poiName"! 也不是 "title"!
  "poiTypeId": 3,
  "imgUrl": "https://dimg04.c-ctrip.com/images/0106912000nwrrbv21350_C_750_1000.jpg"
                                   ← 不是 "imageList" 也不是 "images"!
}
```

**提取**:
```python
poi = pi.get("imageStyleInfo", {}).get("poiInfo", {}).get("ImagePoiList", [])
for p in poi:
    name = p.get("name")  # ⚠️ 不是 "poiName"
    u = p.get("imgUrl")   # ⚠️ 不是 "imageList" / "images"
```

### 3. 携程社区攻略封面 (3+ 张, 按 expertInfo.datas[] 数量)

**字段**: `expertInfo.datas[].coverImageUrl`

**单条结构**:
```json
{
  "id": 140988261,
  "title": "🌋闯入布罗莫火山: 一场极致的冒险之旅",
  "exportTitle": "攻略社区",
  "coverImageUrl": "https://dimg04.c-ctrip.com/images/1me0212000jwp2vki4551_W_640_10000_Q90.jpg?proc=source/tripcommunity",
  "imageList": [{"url": "...", "thumbUrl": "..."}],
  "author": {"nickName": "印尼(巴厘岛)全境游玩", "avatarUrl": "..."},
  "likeCount": 5,
  "productId": 42461732,
  "productName": "印度尼西亚巴厘岛+泗水+布罗莫火山+伊真火山7日6晚私家团"
}
```

**注意**: `expertInfo.summary` 标了"全部 N / 攻略社区 M / 点评 K" 分类, `datas[]` 是排序后的列表。

### 4. 产品经理推荐图 (1 张)

**字段**: `PMRecomendInfo.PMPicturesUrl` (顶层字符串)

```json
"PMRecomendInfo": {
  "PMPicturesUrl": "https://dimg04.c-ctrip.com/images/30080k000000bs0191724.jpg",
  "RecommendList": [
    {"DescDetail": "...", "RecommendTag": "缤纷景点", "CategoryId": 4},
    {"DescDetail": "...", "RecommendTag": "超值赠送", "CategoryId": 7},
    {"DescDetail": "...", "RecommendTag": "服务保障", "CategoryId": 1}
  ]
}
```

**注意**: `PMRecomendInfo.RecommendList[]` 是 3 条**卖点文案**, 不是图。PMPicturesUrl 是单独的封面图。

## 完整 Python 提取 + 下载脚本

```python
import json, re, subprocess, os
j = json.load(open("/opt/data/ctrip-data/xhr_graphql_ProductInfo_2nd_V3_h5.json"))
pi = j["data"]["productInfo"]
OUT = f"/opt/data/ctrip-data/img_{pi['groupCard']['cards'][0]['productId']}"
os.makedirs(OUT, exist_ok=True)

all_imgs = []

# 1) DescriptionInfo
intro = pi["DescriptionInfo"]["Introduction"]
for u in re.findall(r'<img[^>]*src="([^"]+)"', intro):
    all_imgs.append(("desc", "banner", u))

# 2) POI
poi = pi.get("imageStyleInfo", {}).get("poiInfo", {}).get("ImagePoiList", [])
for p in poi:
    name = p.get("name", "unknown")
    u = p.get("imgUrl", "")
    safe_name = re.sub(r'[\\/ ]', '_', name)
    if u: all_imgs.append(("poi", safe_name, u))

# 3) expertInfo
ei = pi.get("expertInfo", {}).get("datas", [])
for i, d in enumerate(ei):
    u = d.get("coverImageUrl", "")
    if u: all_imgs.append((f"expert_{i}", d.get("title", "?")[:30], u))

# 4) PMRecomendInfo
pmr = pi.get("PMRecomendInfo", {})
if pmr.get("PMPicturesUrl"):
    all_imgs.append(("pm", "PM推荐", pmr["PMPicturesUrl"]))

# 下载
ok = 0
for source, name, u in all_imgs:
    fn = f"{OUT}/{source}_{name[:40]}.jpg"
    r = subprocess.run(["curl", "-sL", "-o", fn, u], capture_output=True, timeout=30)
    if os.path.exists(fn) and os.path.getsize(fn) > 1000:
        ok += 1

print(f"下载: {ok}/{len(all_imgs)} → {OUT}")
```

## 常见下载失败原因

| 现象 | 原因 | 解法 |
|---|---|---|
| 0 字节 | URL 缺 query string 后的 `?proc=...` 部分, 携程 CDN 拒绝 | **直接用原 URL, 不要剥 `?proc=...`** |
| 404 | 文件被携程清 | 跳过这条, 标"图失效" |
| 30s 超时 | 印尼 CDN 偶尔慢 | 给 curl 加 `--max-time 30` |
| 下载成功但 PIL 读不了 | 是 HTML 错误页 | 检查文件 size < 10KB → 重新抓 |

## vision_analyze 限制 (2026-06-06 实测)

- **文件 > 1MB**: 直接 413 Request Entity Too Large
- **任意大小**: mcphub 中转返 404 Invalid OAuth
- **解决**: 用 PIL 压缩到 800px 宽 (thumbnail((800, 800)), quality=85), **但本环境 vision 工具本身不通, 压缩也救不了**
- **替代方案**: 携程原图直链 + 用户在浏览器开, 或者 PIL 提取 EXIF / 平均颜色当占位

## 落盘 manifest.json 模板

```json
{
  "product_id": 42461732,
  "captured_at": "2026-06-06T21:18:00+08:00",
  "images": [
    {"source": "desc", "name": "banner", "url": "https://dimg04...", "local": "/opt/data/ctrip-data/img_42461732/desc_banner.jpg", "size": 1263321},
    {"source": "poi", "name": "爪哇岛", "url": "https://dimg04...", "local": ".../poi_爪哇岛.jpg", "size": 216011}
  ]
}
```
