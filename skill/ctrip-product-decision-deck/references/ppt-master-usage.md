# ppt-master 命令链速查

## 项目初始化

```bash
cd /opt/data/skills/ppt-master/skills/ppt-master
python3 scripts/project_manager.py init <slug>_ppt169 --format ppt169
```

生成的目录:
```
projects/<slug>/
├── design_spec.md          ← 写
├── spec_lock.md            ← 写
├── svg_output/             ← 21 个 .svg 写这里
└── exports/                ← 最终 .pptx
```

## 必走 venv

**系统 python 没 pip, 装 Pillow 用**:
```bash
/opt/data/.venv/bin/python scripts/finalize_svg.py <项目绝对路径>
```

(`/opt/data/.venv/lib/python3.11/site-packages/PIL`)

## 三步走命令链

```bash
# 1. 质量检查 (0 error 才能进下一步)
/opt/data/.venv/bin/python scripts/svg_quality_checker.py <项目绝对路径>

# 2. Finalize (PIL 依赖)
/opt/data/.venv/bin/python scripts/finalize_svg.py <项目绝对路径>

# 3. SVG → PPTX
/opt/data/.venv/bin/python scripts/svg_to_pptx.py <项目绝对路径>
```

## 验证产物

```bash
/opt/data/.venv/bin/python -c "
from pptx import Presentation
p = Presentation('<产物路径>')
print(f'页数: {len(p.slides)}')
print(f'尺寸: {p.slide_width/914400:.2f} x {p.slide_height/914400:.2f} 英寸')
for i, s in enumerate(p.slides, 1):
    print(f'  P{i}: {len(s.shapes)} shapes')
"
```

**期望: 21 页 · 13.33 × 7.50 英寸 · 每页 7-11 shapes**。

## 71 个图表模板

```
/opt/data/skills/ppt-master/skills/ppt-master/templates/charts/
```

高频:
- `bar_chart.svg` — 价格日历
- `line_chart.svg` — 趋势
- `kpi_cards.svg` — 决策 KPI
- `timeline.svg` — 单日行程
- `matrix_2x2.svg` — 风险
- `horizontal_bar_chart.svg` — 竞品
- `comparison_table.svg` — 班期库存
- `waterfall_chart.svg` — 预算拆解

**用法**: 参考对应 `chart-plot-area` 注释,改数据 + 改颜色 + 改文字。

## 历史案例(避免重踩)

- `case-study-bali-2026-06-05.md` — Bali 12 页(2026-06-05 出过的问题: XML 嵌套引号 / symbol+use / spec_lock 颜色穷举 / minimax 余额)
- `case-p69762187-2026-07-04.md` — 印尼 21 页(本次)

## 转换策略

`svg_to_pptx.py` 把 SVG 当**Native PowerPoint 元素**转(不转成图片):
- ✅ `<rect>` → pptx rect
- ✅ `<text>` → pptx text run
- ✅ `<line>` → pptx connector
- ❌ `<image>` (内嵌 base64) → 失败时 fallback 图片
- ❌ `<filter>` / `<gradient>` → 简化为单色
