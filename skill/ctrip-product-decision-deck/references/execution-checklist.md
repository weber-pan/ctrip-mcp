# 同类任务执行 checklist —— 可直接照搬

> 把 case-p69762187 案例转成可执行清单。下次拿到 p<productId> + 出发日期 + 人数,按这 8 步走。

## Step 0: 触发确认 (1 句)

确认用户意图是"出 PPT 决策手册"而非"出 md 报告"或"出 PDF"。
如果是 PDF 报告,加载 `ctrip-product-report`;如果是 PPT 决策,加载本 skill。

## Step 1: 加载上游数据 (1-2 tool calls)

```bash
ls /opt/data/ctrip-data/ | grep -E "xhr.*${PID}|price_calendar_${PID}|getCommentSummary_${PID}"
```

期望 4-6 个 JSON。**少了哪个,补抓** (用 `mcp_mcphub_smart_call_tool` 调 `ctrip_spa_capture`)。

## Step 2: 多 MCP 论证 (3-5 tool calls)

按优先级:

1. `携程-wendao_query` × 3-5 轮 (气候/政策/真实评价)
2. `AI_Go_Hotel_MCP-searchHotels` × 1 (酒店区域)
3. `variflight` (航班实时) —— **失败 fallback 携程主接口 FlightInfoList**
4. `高德` (转车距离,可选)

每次调用完,把"结论+数据+来源"写进 `/opt/data/ctrip-data/REPORT_${PID}_e2e.md`。

## Step 3: Eight Confirmations 一次过 (0 tool calls 问用户)

内部设计 8 字段,只在末尾用 1 句话问"要不要改风格/页数"。

## Step 4: 章节确认 1 句 (1 turn)

给用户看 7 大块,问 "21 页可压到 12 页或加到 30 页,改 X 吗?"。**只问 1 件事**。

## Step 5: ppt-master 命令链 (~30 tool calls)

```bash
# 1. 拉项目
cd /opt/data/skills/ppt-master/skills/ppt-master
python3 scripts/project_manager.py init <slug>_ppt169 --format ppt169

# 2. 写 design_spec + spec_lock (按 templates/)

# 3. 21 个 SVG 按 chapter-blueprint.md 写 (write_file 批量)

# 4. 必走 venv
/opt/data/.venv/bin/python scripts/svg_quality_checker.py <项目>
/opt/data/.venv/bin/python scripts/finalize_svg.py <项目>
/opt/data/.venv/bin/python scripts/svg_to_pptx.py <项目>

# 5. 验证
/opt/data/.venv/bin/python -c "from pptx import Presentation; p=Presentation('<产物>'); print(len(p.slides))"
```

期望 50 次 tool calls 完成 (21 SVG + 1 check + 1 finalize + 1 svg_to_pptx + 22 verify)。

## Step 6: 4 坑修复 (1-2 tool calls)

跑 quality_checker 抓 ERROR,grep "ERROR" 找错。

| 错 | 修法 |
|---|---|
| Invalid XML line 76 col 131 | `&` 改 `&amp;` |
| marker-end 无 marker | 改纯 `<line>` |
| spec_lock drift | 补登记颜色到 spec_lock.md |
| Converted 0 elements | inline `<use>` 引用 |

修完再跑,直到 0 error。

## Step 7: 交付 (1 tool call)

```bash
cp <项目>/exports/*.pptx /opt/data/home/workspace/<产品名>_<人数>_<日期>_决策手册.pptx
```

提示用户:页数 + 数据源 + 自费标记。

## Step 8: 沉淀 case (1 turn 写 references/case-*.md)

每次同类任务,**复盘 1 份 case** 写进 references/:
- 8 字段实际值
- 客户原话
- 数据闭环路径
- 坑 + 修法
- 下次同类提示

## 失败模式 (1 hit 立刻停)

- ❌ ctrip-mcp get_product 报 `server.py:149 NoneType` —— **别修,直接切 e2e 重抓**
- ❌ variflight 无结果 —— **fallback 携程主接口 FlightInfoList**
- ❌ tool calls > 70 —— **回 Step 4 砍章节数**
- ❌ quality_checker 报 5+ 错 —— **整批 SVG 重写,不要逐个修**
- ❌ pptx 验证页数 ≠ 21 —— **检查 svg_to_pptx 输出,Converted 数 vs 期望**

## 期望时长

- 全流程: 5-8 分钟
- 主要耗时: 21 个 SVG write_file (人写约 1-2 分钟/页)
- 多 MCP 论证: 30-60 秒
- ppt-master 命令链: 30-60 秒

**如果超 10 分钟,优先查 quality_checker 错,不要从头返工**。
