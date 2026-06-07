# 携程产品页全量图源(extract_more 没抓的)

`ctrip-spa-capture/scripts/extract_images.py` 只抓 **4 类**:desc+poi+expert+pm = ~16 张。

**实际携程 `xhr_ProductInfo_2nd_V3_h5_<id>.json` 里至少 6 类 URL**:

| 类别 | JSON 路径 | 数量 | 用途 |
|------|-----------|------|------|
| **Description banner** | `DescriptionInfo.Introduction` (HTML img) | 3-5 | 营销 banner / 产品特色 |
| **POI 景点图** | `imageStyleInfo.poiInfo.ImagePoiList[].imgUrl` | 6-9 | 景点大图 |
| **Hotel 酒店实景** | `imageStyleInfo.hotelInfo.imageHotelList[].imageList[].imgUrl` | **9 家 × 3 = 27 张** | 真实酒店图 |
| **评论附件(游客实拍)** | `commentInfo.comments[].attachments[].url` | 2-5/条 | 真实旅游画面 |
| **竞品推荐** | `productExtend.MoreRecommendProductList[].ImageUrl` | 6-8 | 竞品 banner |
| **GlobalRanking 景点大图** | `TravelIntroductionInfo.IntroductionInfoList[].DailyList[].ScenicSpotList[].GlobalRankingInfo.ImageUrl` | 5-12(去重后 5-8) | 携程官方景点图 |
| PM 经理 | `PMRecomendInfo.PMPicturesUrl` | 1 | 联系人 |
| TravelSummaryModule icon | `TravelOverviewInfo.TravelSummaryModuleList[].IconUrl` | 5 | 摘要小图标 |

**漏抓 4 类 = hotel+comment+competitor+ranking = 45+ 张图,必须手动补**。

## 手动补图脚本 (Node,绕开 Python 字符串过滤)

```javascript
// /tmp/dl_all.js
const fs = require('fs');
const https = require('https');

const DATA = '/opt/data/ctrip-data';
const OUT = `${DATA}/img_69762187`;
fs.mkdirSync(OUT, { recursive: true });

const pi = JSON.parse(fs.readFileSync(`${DATA}/xhr_ProductInfo_2nd_V3_h5_69762187.json`,'utf-8'))
  .data.productInfo;

function dl(url, local) {
  return new Promise((resolve) => {
    if (fs.existsSync(local) && fs.statSync(local).size > 1000) return resolve('skip');
    const req = https.get(url, { headers: { 'User-Agent': 'Mozilla/5.0', Referer: 'https://m.ctrip.com/' } }, res => {
      if (res.statusCode >= 300 && res.statusCode < 400) return resolve(dl(res.headers.location, local));
      const f = fs.createWriteStream(local);
      res.pipe(f);
      f.on('finish', () => f.close(() => resolve('ok')));
    });
    req.on('error', () => resolve('fail'));
  });
}

(async () => {
  // 1) Hotel
  for (let i = 0; i < pi.imageStyleInfo.hotelInfo.imageHotelList.length; i++) {
    const h = pi.imageStyleInfo.hotelInfo.imageHotelList[i];
    const name = h.name.replace(/\//g, '_');
    for (let j = 0; j < (h.imageList||[]).length; j++) {
      const url = h.imageList[j].imgUrl;
      const ext = url.includes('.png') ? 'png' : 'jpg';
      await dl(url, `${OUT}/hotel_${i}_${name}_${j}.${ext}`);
    }
  }

  // 2) Comment
  for (let i = 0; i < pi.commentInfo.comments.length; i++) {
    const atts = pi.commentInfo.comments[i].attachments || [];
    for (let j = 0; j < atts.length; j++) {
      const url = atts[j].url;
      const ext = url.includes('.png') ? 'png' : 'jpg';
      await dl(url, `${OUT}/comment_${i}_${j}.${ext}`);
    }
  }

  // 3) Competitor
  for (let i = 0; i < pi.productExtend.MoreRecommendProductList.length; i++) {
    const p = pi.productExtend.MoreRecommendProductList[i];
    const url = p.ImageUrl;
    const ext = url.includes('.png') ? 'png' : 'jpg';
    await dl(url, `${OUT}/competitor_${i}_${p.ProductId || i}.${ext}`);
  }

  // 4) Ranking (dedup)
  const seen = new Set();
  function walk(obj) {
    if (typeof obj !== 'object' || !obj) return;
    if (obj.GlobalRankingInfo && obj.GlobalRankingInfo.ImageUrl) {
      const u = obj.GlobalRankingInfo.ImageUrl;
      if (!seen.has(u)) {
        seen.add(u);
        dl(u, `${OUT}/ranking_${seen.size}.jpg`);
      }
    }
    for (const v of Object.values(obj)) walk(v);
  }
  walk(pi);
  console.log('done');
})();
```

## 命名误导陷阱(2026-06-07 实证)

下载下来**别信文件名**!携程 POI 字段名是营销标签,不是真实景点:

| 字段名 | 实际内容(用 M3 视觉确认) |
|--------|---------------------------|
| `poi_爪哇岛.jpg` | ❌ **不是布罗莫火山,是清真寺航拍** |
| `poi_佩妮达岛.jpg` | ✅ Kelingking Beach 精灵坠崖 |
| `poi_双子湖.jpg` | ✅ 高山湖泊+绿山+蓝天(疑似 Twin Lake) |
| `poi_罗威纳海滩.jpg` | ✅ 黑色火山沙海滩(无海豚) |
| `poi_德格拉朗梯田.jpg` | ✅ Tegallalang 梯田 |
| `poi_水神庙.jpg` | ✅ Pura Ulun Danu Beratan |
| `poi_金塔马尼高地.jpg` | ✅ 巴图尔湖+阿贡火山(云遮) |
| `desc_0/1/2.jpg` | ❌ **携程营销 banner,不是景点实图** |

**M3 视觉读图必走** — 不读就直接用图 = 把清真寺当布罗莫,把营销话术当行程。