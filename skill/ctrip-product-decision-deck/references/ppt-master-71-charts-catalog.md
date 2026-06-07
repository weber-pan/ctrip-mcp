# ppt-master 71 图表速查 —— 自拼 vs 复用决策表

> 用户原话: "配色那么丑 ppt-master 没有模版吗"
> 答案: **71 个图表模板** 在 `/opt/data/skills/ppt-master/skills/ppt-master/templates/charts/`
> **别自拼,先复用**。自绘一章 = 多花 5-8 tool calls,复用 = 1 tool call 改数据。

## 必复用(8 个,本任务 100% 用到)

| 模板 | 用途 | 出现页 |
|---|---|---|
| `bar_chart.svg` | 价格日历 / 单维度对比 | P07 |
| `line_chart.svg` | 趋势 / 时序 | P08 |
| `kpi_cards.svg` | 决策数字 / 多维评分 | P10 |
| `timeline.svg` | 单日时间轴 | P13-16 |
| `matrix_2x2.svg` | 强度×风险 / 决策矩阵 | P12 |
| `horizontal_bar_chart.svg` | 竞品对比 / 排名 | P17 |
| `comparison_table.svg` | 多列对比 / 班期库存 | P18 |
| `waterfall_chart.svg` | 预算拆解 / 累计堆叠 | P19 |

## 按需复用(20+ 个,本任务 0 用但下次可能用)

- `donut_chart.svg` / `pie_chart.svg` —— 占比
- `stacked_bar_chart.svg` / `grouped_bar_chart.svg` —— 多维堆叠
- `area_chart.svg` / `stacked_area.svg` —— 面积趋势
- `scatter_plot.svg` / `bubble_chart.svg` —— 散点
- `funnel_chart.svg` —— 转化漏斗
- `radar_chart.svg` —— 能力雷达
- `heatmap.svg` —— 热力
- `gantt_chart.svg` —— 甘特
- `sankey_diagram.svg` —— 桑基
- `box_plot.svg` / `violin_plot.svg` —— 分布
- `candlestick_chart.svg` —— 金融
- `geographic_map.svg` / `choropleth_map.svg` —— 地图

## 自拼(3 类,只能用自绘)

- **封面 / 目录** —— 渐变 hero + 大字,自拼
- **路线地图** —— 简化地理 + 标号,自拼
- **出发清单** —— 4 列 checklist,自拼

## 用法 (3 步)

```bash
# 1. 看模板
ls /opt/data/skills/ppt-master/skills/ppt-master/templates/charts/

# 2. 找注释
grep -A 1 "chart-plot-area" templates/charts/bar_chart.svg
# 输出: <!-- chart-plot-area: x_min=80,y_min=200,x_max=1180,y_max=560 -->

# 3. 复制模板,改数据 + 改颜色 + 改文字
cp bar_chart.svg my_chart.svg
# (然后 write_file 覆盖)
```

## 复用率目标

**21 页 PPT 中至少 8 页应 0 自绘**(bar/line/kpi/timeline/matrix/horizontal_bar/comparison_table/waterfall)。

**自绘 ≤ 13 页**:封面 + 目录 + 核心结论 + 真实航班 + 7日概览 + 真实酒店 + 路线图 + 4-5 个单日详情 + 出发清单 + 决策选项。

如果发现自绘数 > 复用数,**回到模板库里找**。
