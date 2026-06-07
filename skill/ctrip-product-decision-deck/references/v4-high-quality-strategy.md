# v4 高质量 PPT 制作策略(2026-06-07)

> **3-5 工具/turn 限制**下,做 28 页高质量 PPT 不能每页从 0 写 SVG。改 5 张关键页 + 复用 v2 其余 = 平衡质量与 quota。

## 1. 5 张必改的关键页(旅客视角 + 真图)

| 页 | 必改原因 | 数据源 |
|---|---|---|
| **P01 封面** | 杂志感 + 主图全幅 + 渐变蒙版 | desc_0 或 ranking_5(精灵坠崖) |
| **P06 5 段真实酒店** | 不能用 9 家备选,要 5 家真实 | `getShoppingDetail.Hotel.Hotels` |
| **P14 布罗莫+塞武** | 2 张真图 + 2 日行程表 | ranking_1+2 |
| **P15 伊真** | 火山口 + 林塘玻璃穹顶 + 蓝火风险框 | ranking_3 + hotel_6 |
| **P16 佩妮达** | 精灵坠崖 + 钻石沙滩 + 2 选 1 套餐 | ranking_4+5 |
| **(新增) P20 退订** | 5 阶梯柱状图 + 3 大预案 | dom_text 违约金字段 |

## 2. 复用 v2 其余 22 页

```bash
# 复制 v2 svg 到 v4 项目
cp projects/<v2_name>/svg_output/*.svg projects/<v4_name>/svg_output/
```

复用前提:v2 已经走过 13 色板 + 4 字体 + 4 坑 排查,质量已经达标。

## 3. 5 张关键页 SVG 模板(已验证可编译)

### P01 封面模板

```python
'<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720">'
'  <defs>'
'    <linearGradient id="cover_fade" x1="0" y1="0" x2="0" y2="1">'
'      <stop offset="0" stop-color="#000" stop-opacity="0.15"/>'
'      <stop offset="0.5" stop-color="#000" stop-opacity="0.5"/>'
'      <stop offset="1" stop-color="#000" stop-opacity="0.85"/>'
'    </linearGradient>'
'  </defs>'
'  <image href="data:image/jpeg;base64,{cover_b64}" x="0" y="0" width="1280" height="720" preserveAspectRatio="xMidYMid slice"/>'
'  <rect x="0" y="0" width="1280" height="720" fill="url(#cover_fade)"/>'
'  <text x="60" y="80" font-family="Georgia, serif" font-size="18" fill="#D4A017" letter-spacing="6">CTRIP · VACATIONS</text>'
'  <text x="60" y="280" font-family="Georgia, serif" font-size="72" fill="#FFFFFF" font-weight="bold">主标题</text>'
'  <rect x="0" y="620" width="1280" height="100" fill="#0F1A24" opacity="0.92"/>'
'  <text x="60" y="660" font-family="Consolas, monospace" font-size="18" fill="#FFFFFF">5 段酒店 / 7 日行程 / 60+ 真实图 / 28 页决策手册</text>'
'</svg>'
```

### P06 5 段酒店模板(主图 + 3 子图 + 5 段表)

- 主图 560×340(香格里拉/喜来登/希尔顿 主图)
- 3 子图 280×160(其他酒店子图)
- 右侧 270×350 表:5 段入住 + 不可取消红标 + 2 晚可取消绿标
- 底部 1160×120:跟着景点走的"跟着景点走"说明

### P20 退订风险模板(5 阶梯柱状图)

```python
# 5 阶梯(纵轴 = 损失 ¥,横轴 = 距出发日)
'<rect x="0" y="240" width="100" height="40" fill="#3E6B53" opacity="0.85"/>'   # 30 天前 0%
'<rect x="105" y="234" width="100" height="46" fill="#3E6B53" opacity="0.7"/>'  # 29-15 5%
'<rect x="210" y="216" width="100" height="64" fill="#D4A017" opacity="0.7"/>'  # 14-7 20%
'<rect x="315" y="160" width="100" height="120" fill="#C0392B" opacity="0.7"/>' # 6-4 50%
'<rect x="420" y="136" width="100" height="144" fill="#C0392B" opacity="0.85"/>' # 3-1 60%
'<rect x="525" y="112" width="100" height="168" fill="#C0392B" opacity="0.95"/>' # 当日 70%
```

## 4. ffmpeg 缩图(平衡清晰度 + base64 大小)

```bash
# 1200px q=4 平衡清晰度(100-500KB/张)
ffmpeg -y -i <src> -vf scale=1200:-1 -q:v 4 <dst>.jpg

# base64 翻 1.33 倍,9 张总 3MB(超 5MB 会爆 rsvg)
```

## 5. 编译命令链

```bash
cd /opt/data/skills/ppt-master/skills/ppt-master
# 1. 质量检查(必走)
python3 scripts/svg_quality_checker.py projects/<v4>/svg_output/
# 2. 编译
python3 scripts/svg_to_pptx.py "projects/<v4>"
# 3. 复制到 workspace
cp projects/<v4>/exports/*.pptx /opt/data/home/workspace/<user_file>.pptx
```

## 6. 验证(via python-pptx)

```python
from pptx import Presentation
p = Presentation('/opt/data/home/workspace/<file>.pptx')
print(f'页数: {len(p.slides)} · 尺寸: {p.slide_width/914400:.2f}x{p.slide_height/914400:.2f} 英寸')
```

## 7. 真图嵌 SVG 5 大坑(踩过)

1. **bundle 总大小 ≤ 5MB** = 9 张 @ ~300KB base64 = 3MB OK
2. **`<image href="data:image/jpeg;base64,..."` 不加 `xlink:href`**(rsvg 兼容)
3. **`preserveAspectRatio="xMidYMid slice"`** 全幅图必加(防拉伸)
4. **ffmpeg 缩图后必须 base64 bundle** 一次写,不要每张单独读
5. **`<rect fill="url(#cover_fade)"/>` 蒙版放 image 之后**(否则盖住图)
