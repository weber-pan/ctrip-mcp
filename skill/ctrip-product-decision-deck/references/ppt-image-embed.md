# PPT 嵌真图:5 步法 + 5 页模板(2026-06-07 v3 真图版总结)

> **用户原话**:"你忘记要下载下来 分析的吗" + "你确定所有宣传图都拿到了" + "你本身也是图像模态的吧 你可以读 携程官网 产品的图片吧 你忘记要下载下来 分析的吗"
>
> **核心结论**:**PPT 不嵌产品真图 = 视觉单调 = 用户吐槽"内容简单 / 配色丑"**。**携程产品 SPA 抓 16 张不够,要全量 6 类 60+ 张**;**M3 视觉读完再决定用哪张**。

## 1. 为什么必须嵌图(用户原话触发)

- 用户问"你确定所有宣传图都拿到了" — **6 类图只抓 4 类 = 漏 45+ 张**(`extract_images.py` 只抓 desc+poi+expert+pm)
- 用户问"你本身是图像模态" — **M3 走 minimax API `type:image` 有原生视觉**(绕开 `vision_analyze` 死网关),不调 M3 视觉 = 不知道图是什么
- 用户提"模板" — ppt-master 有 71 图表模板,但**自拼封面/单日详情 5 页时必须嵌真图**,模板帮不上

## 2. 5 步嵌图法(强制流程)

```bash
# 步骤 1: M3 视觉精选 6-8 张图(从全量 60+ 里选)
# 用 m3-native-vision skill 的 m3_vision.py,prompt 见 §4

# 步骤 2: ffmpeg 缩图(800px q=5 = 50-200KB,平衡清晰度+文件大小)
mkdir -p /tmp/ppt_imgs
for f in ranking_2.jpg ranking_3.jpg ranking_5.jpg hotel_5_*.jpg hotel_0_*.jpg hotel_6_*.jpg; do
  ffmpeg -y -i "/opt/data/ctrip-data/img_$PID/$f" -vf "scale=800:-1" -q:v 5 "/tmp/ppt_imgs/$f"
done

# 步骤 3: base64 bundle 写 json(SVG 引用)
python3 -c "
import base64, json
from pathlib import Path
bundle = {}
for p in Path('/tmp/ppt_imgs').glob('*.jpg'):
    bundle[p.name] = f'data:image/jpeg;base64,{base64.b64encode(p.read_bytes()).decode()}'
Path('/tmp/ppt_imgs/bundle.json').write_text(json.dumps(bundle))
print(f'bundle: {len(bundle)} 张')
"

# 步骤 4: SVG <image href="data:..."> 嵌 base64
# 模板见 §3

# 步骤 5: ppt-master 编译(走原有 3 步)
cd /opt/data/skills/ppt-master/skills/ppt-master
/opt/data/.venv/bin/python scripts/finalize_svg.py projects/<name>/
/opt/data/.venv/bin/python scripts/svg_to_pptx.py "projects/<name>"
```

**关键参数**:
- **800px q=5**: 100-200KB/张(可上 1200px q=3 = 200-300KB 用于封面)
- **base64 翻 1.33 倍**: 6 张 200KB → 1.6MB 嵌 SVG,远 < 64MB body 限制
- **M3 视觉单图 ~500 input + 800 output tokens**(2026-06-07 实测)

## 3. 5 页必嵌模板

### P01 封面 = 主图全幅 + 渐变蒙版 + 白字

```xml
<svg viewBox="0 0 1280 720">
  <defs>
    <linearGradient id="cg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="rgba(0,0,0,0.25)"/>
      <stop offset="60%" stop-color="rgba(0,0,0,0.45)"/>
      <stop offset="100%" stop-color="rgba(0,0,0,0.75)"/>
    </linearGradient>
  </defs>
  <image href="data:image/jpeg;base64,..." x="0" y="0" width="1280" height="720" preserveAspectRatio="xMidYMid slice"/>
  <rect x="0" y="0" width="1280" height="720" fill="url(#cg)"/>
  <text x="80" y="450" font-size="68" font-weight="900" fill="#FFFFFF">印尼 7 日 6 晚</text>
  <!-- ... -->
</svg>
```

### P06 真实酒店 = 主图大图 + 4 子图网格 + 文字备选表

```xml
<image href="..." x="80" y="140" width="700" height="380"/>  <!-- 主图 700×380 -->
<image href="..." x="820" y="140" width="200" height="120"/>  <!-- 子图 200×120 -->
<!-- 4 子图 + 文字标注 + 5 家文字备选 -->
```

### P14/P15/P16 单日详情 = 主图 + desc_2 行程表

```xml
<image href="..." x="80" y="140" width="540" height="380"/>  <!-- 主图 540×380 -->
<g transform="translate(660, 140)">
  <rect ... fill="#FFFEF9"/>
  <text>📋 真实行程(M3 从 desc_2 banner 提取)</text>
  <!-- 7 日表格 -->
</g>
```

### P15 暗色页(伊真蓝火) = 黑底 + 蓝火图 + 帐篷图

```xml
<rect fill="#0F1A24"/>  <!-- 深海蓝黑 -->
<text fill="#F5DEB3"/>   <!-- 暖金文字 -->
<text fill="#A0B4C8"/>   <!-- 浅蓝副文 -->
<image href="蓝火图"/>
<image href="帐篷图"/>
```

## 4. M3 视觉问图 prompt 模板

| 图类 | prompt |
|---|---|
| 主图/封面 | "画面内容 / 适合 PPT 哪一页 / 是否适合做品牌主图 / 视觉冲击力" |
| POI 景点 | "这是哪个景点(印尼/巴厘/布罗莫/佩妮达/泗水?)画面内容、构图" |
| 酒店 | "酒店档次(几星)/ 场景(大堂/客房/泳池/外观)/ 适合放 P06 真实酒店页吗" |
| 营销 banner | "完整提取所有文字:1)产品名/标题 2)行程天数路线 3)价格/优惠 4)增值服务 5)团队规则 6)品牌 7)电话/二维码" |
| 景点大图(ranking) | "印尼哪个景点?简短描述" |
| 点评实拍图 | "游客发的实拍图,反映什么体验" |

## 5. 5 大避坑(2026-06-07 v3 真图版踩过)

1. **别信文件名**: 携程 POI 字段名是营销标签 — `poi_爪哇岛.jpg` 是清真寺不是布罗莫,`desc_0/1/2.jpg` 是携程营销 banner 不是景点实图
2. **别跳过 M3 视觉**: 不读就直接用图 = 把清真寺当布罗莫,把营销话术当行程(P14 之前 P14 文字行程 vs M3 提取的 desc_2 真实行程差异巨大)
3. **别用 PNG 直接嵌**: PNG base64 比 JPEG 大 3-5 倍,800px q=5 JPEG 是性价比甜蜜点
4. **别用 vision_analyze 工具**: 2026-06-07 server 端 nginx 404,改用 m3-native-vision 直调 minimax API
5. **别漏暗色页配色**: 伊真 P15 用黑底 + 蓝火图(常规页用 #F5F1E8 米色),否则图看不清

## 6. v3 真图版前后对比(p69762187)

| 项 | v1/v2(纯色块) | **v3(真图版)** |
|---|---|---|
| P01 封面 | 纯色+白字 | 佩妮达精灵坠崖全幅 |
| P06 酒店 | 5 家虚构 | 9 家真备选 + 香格里拉大图 |
| P14 布罗莫 | 文字+色块 | 布罗莫火山图 + 真实行程表 |
| P15 伊真 | 文字 | 蓝火图 + 林塘帐篷图双图 |
| P16 佩妮达 | 文字 | Kelingking Beach 真图 |
| **PPT 文件大小** | 109KB / 127KB | **797 KB**(图占大头) |
| **视觉冲击力** | 单调 | 杂志感/海岛风 |

## 7. See also

- [m3-native-vision](../../mlops/m3-native-vision/SKILL.md) — M3 直调 minimax API 完整模板
- [all-image-sources.md](all-image-sources.md) — 6 类图源全清单
- [image-pipeline.md](image-pipeline.md) — ffmpeg/rsvg 缩图 + PNG 预览命令链
- [chapter-blueprint.md](chapter-blueprint.md) — 21-25 页章节模板
