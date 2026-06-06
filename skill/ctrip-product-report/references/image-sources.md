# 携程 4 类图片来源 + 字段名坑

> 验证时间: 2026-06-06  
> 验证数据: p42461732 / p69762187 / p64158367

## 4 类图片源(总 15+ 张/产品)

| 来源 | 字段 | 数量/产品 | URL pattern |
|---|---|---|---|
| **产品介绍 banner** | `DescriptionInfo.Introduction` (HTML `<img>`) | 2-3 张 | `https://dimg04.c-ctrip.com/images/0305k12000xxx_xxx.jpg` |
| **POI 景点图** | `imageStyleInfo.poiInfo.ImagePoiList[].imgUrl` | 7-9 张 | `https://dimg04.c-ctrip.com/images/{id}_C_750_1000.jpg` |
| **携程社区攻略** | `expertInfo.datas[].coverImageUrl` | 0-10 张(看产品) | `..._W_640_10000_Q90.jpg?proc=source/tripcommunity` |
| **产品经理推荐** | `PMRecomendInfo.PMPicturesUrl` | 1 张 | `https://dimg04.c-ctrip.com/images/30080k000000bs0191724.jpg` |
| **品牌标签** (额外) | `brandTag.ImgUrl.{single,half,mini,new}` | 4 张 PNG | `https://pic.c-ctrip.com/VacationH5Pic/tourpic/...` |

**总计**: 15+ 张图(从 12 张基础 + 0~10 张攻略封面 + 4 张品牌 = 16-26 张)

## 字段名坑(踩过 N 次)

| 错误字段 | 正确字段 | 原因 |
|---|---|---|
| `p.get('poiName')` | `p.get('name')` | 携程统一用小写 name |
| `p.get('imageList')` | `p.get('imgUrl')` | 单数 + 驼峰 |
| `p.get('imageUrl')` | `p.get('imgUrl')` | 缩写 |
| `p.get('hotelId')` (大写) | `p.get('hotelId')` (小写) | 大小写敏感 |
| `pi.get('Title')` (2nd_V3) | `bi.get('Title')` (VPC BasicInfo) | 2nd_V3 缺, VPC 有 |
| `fee['Description']` (FeeInfoList) | `tp['Description']` (TargetPopulationItemList[]) | 中间缺一层 |
| `dom querySelector` 找景点 | `SegmentInfo.Segments[]` | SPA DOM 不准 |

## 图片下载 (extract_more.py)

```python
def extract_images(product_id, pi, ei, pmr, bt):
    out_dir = Path(f"/opt/data/ctrip-data/img_{product_id}")
    
    # 1) DescriptionInfo HTML
    intro = pi['DescriptionInfo']['Introduction']
    for i, u in enumerate(re.findall(r'<img[^>]*src="([^"]+)"', intro)):
        curl -sL -o out_dir/desc_{i}.jpg {u}
    
    # 2) POI
    for p in pi['imageStyleInfo']['poiInfo']['ImagePoiList']:
        curl -sL -o out_dir/poi_{p['name']}.jpg {p['imgUrl']}
    
    # 3) expertInfo 攻略封面
    for d in ei.get('datas', []):
        curl -sL -o out_dir/expert_{d['title']}.jpg {d['coverImageUrl']}
    
    # 4) PM
    curl -sL -o out_dir/pm.jpg {pmr['PMPicturesUrl']}
    
    # 5) brandTag (4 尺寸)
    for k, v in bt['ImgUrl'].items():
        curl -sL -o out_dir/brand_{k}.png {v}
```

**注意**:
- 检查 `sz > 1000` (1KB), 过滤失败图
- 落盘 `manifest.json` 记录 url→本地路径映射, 后续报告插入图片用本地路径 (`MEDIA:/opt/data/ctrip-data/img_XXX/...jpg`)

## 报告插入图片(本地路径)

```markdown
MEDIA:/opt/data/ctrip-data/img_69762187/desc_0.jpg
MEDIA:/opt/data/ctrip-data/img_69762187/poi_爪哇岛.jpg
MEDIA:/opt/data/ctrip-data/img_69762187/pm.jpg
```

WebUI 自动渲染。其他平台(钉钉/微信)用 `send_message` 工具, MEDIA: 前缀自动转为 native attachment。

## 验证样例

- `img_42461732/` — 15 张图, 9 POI 命名清晰(爪哇岛/罗威纳海滩/...)
- `img_69762187/` — 15 张图, 7 POI + 4 brand
