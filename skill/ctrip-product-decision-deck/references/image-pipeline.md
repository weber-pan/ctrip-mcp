---
name: image-pipeline
description: 携程 SPA 抓取产出的 16+ 张图(描述/POI/PM/品牌)的处理管道 — ffmpeg 缩图、PNG 预览、vision_analyze 兜底链、嵌入 PPT 工程模板。2026-06-07 p69762187 案例产出。
---

# 携程产品图处理管道

> **触发条件**: ctrip-spa-capture `extract_images.py` 跑完后,`/opt/data/ctrip-data/img_<pid>/` 里有 16+ 张图
> **目标**: 视觉分析 + 嵌入 PPT + PNG 预览发给用户
> **核心痛点**: vision server 端常 404,3.6 MB desc_1.jpg 触发 413(尺寸限制)

## 1. 图清单(典型 16 张分布)

| 类型 | 数量 | 文件名 | 大小典型 |
|---|---|---|---|
| desc 主图 | 3 | `desc_0.jpg` `desc_1.jpg` `desc_2.jpg` | 0.5-3.7 MB ⚠ |
| POI | 7 | `poi_<中文名>.jpg` | 0.1-0.2 MB |
| PM 产品经理 | 1 | `pm.jpg` | 0.6 MB |
| brand | 4 | `brand_*.png` | 0.01-0.05 MB |

> 携程 `desc_1/2.jpg` 经常 3.6 MB(全屏 banner 原图), **第一步必须缩**

## 2. 缩图命令链(ffmpeg,无 PIL 时)

```bash
mkdir -p /tmp/img_small /tmp/img_tiny
SRC=/opt/data/ctrip-data/img_<pid>
OUT=/tmp/img_tiny  # 小预览 (~20 KB/张,够 webui 渲染)

for f in $SRC/*.jpg; do
  ffmpeg -y -i "$f" -vf "scale=400:-1" -q:v 15 \
    "$OUT/$(basename ${f%.jpg})_tiny.jpg" 2>/dev/null
done
```

**尺寸档位**(按 server 端 size limit 调整):

| 档 | 命令 | 输出大小 | 适用 |
|---|---|---|---|
| small 800px | `scale=800:-1 q:v 5` | 100-800 KB | vision_analyze 默认 |
| tiny 400px | `scale=400:-1 q:v 15` | 12-26 KB | vision server 死时硬压 |
| xs 200px | `scale=200:-1 q:v 20` | < 10 KB | 终极兜底 |

**关键坑**:
- **desc_1.jpg 3.6 MB 即使缩到 400px 仍 147 KB** → 触发 413 → 再缩 300px q=20
- **17 KB 也可能 404** → 不是大小问题,是 server routing 死
- **rsvg-convert 不支持 JPG** → 只能用 ffmpeg
- **PIL `_imaging` import 失败**(`/opt/data/.venv` 里 PIL 装坏) → 走 ffmpeg 兜底

## 3. vision_analyze 兜底链(优先级降序)

| 优先级 | 通道 | 触发条件 | 失败动作 |
|---|---|---|---|
| 1 | `vision_analyze(image_url, question)` | server 通 | 拿文字描述 |
| 2 | `vision_analyze` 缩到 800px | 报 413 | ffmpeg 缩图 |
| 3 | ffmpeg 缩 400px q=15 | 仍 404 | 标 vision server 死 |
| 4 | `mmx vision describe --image ...` | hermes 死时绕道 | minimax 余额不足时也挂 |
| 5 | `OCR 识别-GeneralOcrRecognition` | 文字类图 | 经常 TIMEOUT |
| 6 | **发 MEDIA 路径给用户自己看** | 全部不可用 | 诚实交代"我读不了" |

**绝不假装读过**。vision 拿不到 = 拿不到,告诉用户"用你眼睛"。

## 4. 精选复制到 ppt-master `images/`

```bash
PPT_IMG=/opt/data/skills/ppt-master/skills/ppt-master/projects/<name>/images
mkdir -p $PPT_IMG

# 选 4-6 张: 主图 1 + 关键 POI 3-5
cp /opt/data/ctrip-data/img_<pid>/desc_0.jpg $PPT_IMG/
cp /opt/data/ctrip-data/img_<pid>/poi_佩妮达岛.jpg $PPT_IMG/
cp /opt/data/ctrip-data/img_<pid>/poi_爪哇岛.jpg $PPT_IMG/  # 布罗莫代表
cp /opt/data/ctrip-data/img_<pid>/poi_水神庙.jpg $PPT_IMG/
```

**入选标准**:
- `desc_0.jpg` = 主图(必,封面用)
- 关键 POI = 行程必经地(用户最在意的)
- 跳过 brand(质量低,装饰用)
- PM = 看情况(联系页可用)

## 5. PNG 预览(给 webui 渲染用)

```bash
OUT=/opt/data/home/workspace/ppt_screenshots
mkdir -p $OUT

# rsvg-convert SVG → PNG (PPT 同源)
rsvg-convert -w 1600 -o $OUT/<name>.png <svg>
```

> `rsvg-convert` 在 `/usr/bin/`, 不在 PATH 但能直接调
> PPT 内部 SVG 已通过 quality_checker 0 错,PNG 视觉 = PPT 实际样子

## 6. 嵌入 PPT 的 3 个位置(模板)

| 页 | 嵌入方式 | 效果 |
|---|---|---|
| P01 封面 | 全幅 `desc_0.jpg` + 标题叠白字 | 杂志感大幅图 |
| P13-16 单日详情 | 1 张 POI 图 + 当日文字 | 图文对应,记得 |
| P21/P25 客群/收尾 | 1 张氛围图(罗威纳海滩=蜜月) | 场景共鸣 |

**SVG 嵌入图片方法**(在 SVG 里直接引用):
```xml
<image x="40" y="40" width="600" height="400"
       xlink:href="/opt/data/ctrip-data/img_<pid>/desc_0.jpg"/>
```

> svg_to_pptx 转换器是否支持 image href: **当前未实测**;稳妥做法是**先把图缩到 base64 inline**(`<image href="data:image/jpeg;base64,...">`), 或等 ppt-master 工具支持。

## 7. 案例:p69762187 实际跑通(2026-06-07)

| 步骤 | 输入 | 输出 | 状态 |
|---|---|---|---|
| extract_images.py | 抓完 SPA | 16 张图 + manifest.json | ✅ 自动 |
| ffmpeg 缩 400px | 16 张 0.1-3.7 MB | 11 张 12-148 KB tiny | ✅ |
| vision_analyze 11 次 | 11 张 tiny | 全 404 (server 死) | ❌ 通道坏 |
| mmx vision describe | 1 张 jpeg | insufficient balance | ❌ 余额 |
| OCR MCP | 1 张 jpeg | 请求超时 | ❌ 慢 |
| MEDIA 给用户 | 7 张路径 | 用户自己看 | ✅ 兜底 |
| 复制 6 张到 ppt-master images | desc_0 + 5 POI | 嵌入待办 | ✅ 已复制 |

**关键教训**:
- 16 张图 **从一开始就在磁盘上,2026-06-06 自动下载的** — 我漏掉分析,被用户点出
- **vision 不可用时,核心动作是"用 PNG/MEDIA 路径 + 标 vision server 死"**,不是"装看不见"
- 嵌入 PPT 的 image href **当前未验证**;若 svg_to_pptx 失败,降级为 P01 用纯文字 + P13-16 用 emoji 替代视觉

## 8. 后续 TODO(写给下次执行)

- [ ] 验证 svg_to_pptx 是否支持 `<image href="...">` — 如不支持,降级方案
- [ ] 写 `scripts/downscale_for_vision.sh` 一键缩图工具
- [ ] 写 `scripts/select_pp_images.py` 按 POI 关键词自动选 4-6 张精品
- [ ] vision server 复活后,补做 p69762187 11 张图的视觉描述,补进 case md
