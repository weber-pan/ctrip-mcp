# spec_lock.md — <slug>

> **Source of truth**: 本文件是执行锁定,所有 SVG 必须从这里取色/字体/图标。
> **配色**: <N> 色全部锁定,新增必须更新本文件。
> **字体**:仅 <M> 个 stack,且已用 `&quot;` 转义,SVG 端必须完全一致。
> **图标**:仅 <库名> lib。

## 配色(穷举 13 色)

| 角色 | Hex | 含义 |
|---|---|---|
| 主色 1 (海) | #1F4E79 | 品牌蓝 |
| 主色 2 (岛) | #3E6B53 | 海岛绿 |
| 强调 1 (火) | #C0392B | 警示红 |
| 强调 2 (夕) | #D4A017 | 经验黄 |
| 文字主 | #1A1A1A | 标题 |
| 文字辅 | #5C5C5C | 副标题 |
| 文字淡 | #1A1A1A | 正文 |
| 背景 | #FAF6EE | 米色纸 |
| 卡片 | #FFFFFF | 卡片白 |
| 边框 | #D4C5A0 | 1px 边 |
| 海岛地形 | #E8D9B5 | 地图色 |
| 数据正向 | #1F4E79 | KPI 数字 |
| 数据反向 | #C0392B | KPI 警示 |

## 字体(4 stack · 全部 `&quot;` 转义)

```css
font-family: "Microsoft YaHei", sans-serif;                    /* 中文本 */
font-family: Georgia, "Microsoft YaHei", serif;                /* 标题+衬线 */
font-family: Consolas, "Microsoft YaHei", monospace;            /* 数字+等宽 */
font-family: "Microsoft YaHei", "PingFang SC", sans-serif;      /* 兜底 */
```

## 图表类型(20+)

| 图表 | SVG 模板 | 用途 |
|---|---|---|
| bar_chart | bar_chart.svg | 价格日历 |
| line_chart | line_chart.svg | 趋势 |
| kpi_cards | kpi_cards.svg | 决策 KPI |
| timeline | timeline.svg | 单日行程 |
| matrix_2x2 | matrix_2x2.svg | 强度风险 |
| horizontal_bar | horizontal_bar_chart.svg | 竞品 |
| comparison_table | comparison_table.svg | 班期库存 |
| waterfall | waterfall_chart.svg | 预算拆解 |
| illustration | 自绘 | 路线地图 |

## 图标库(选 1)

- chunk-filled(粗) / tabler-filled(中) / tabler-outline(细) / phosphor-duotone
- 用法: 复制到 SVG `<symbol>` 或 inline `<path>`

## 数据真实度

| 色 | 含义 | 例子 |
|---|---|---|
| #3E6B53 绿 | ✅ e2e 核实 | 跟团价 |
| #1F4E79 蓝 | 🛡 政策 | 落地签 |
| #D4A017 黄 | ⚠ 经验 | 自费 |
| #C0392B 红 | ❌ 警示 | 降级 |
