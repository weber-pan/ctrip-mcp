# ctrip-mcp (携程 MCP - 真抓版)

> 配套姊妹仓库:[xiecheng-mcp](https://gitee.com/weber-pan/xiecheng-mcp)(wendao LLM 兜底版)
> 配套 Agent skill: `skill/ctrip-product-research/` umbrella → `ctrip-spa-capture` + `ctrip-product-report`

把携程 m 端 h5 SPA 内部 graphql/soa 接口封装为 [Model Context Protocol](MCP) server。
**核心差异**:不走携程"问道"LLM 兜底,直接 Playwright + Chromium + fetch hook 拦截 SPA 内部接口,拿到一手 JSON。

---

## 0. 60 秒从 0 跑起来 (Bootstrap)

```bash
# 任意环境 (Mac / Linux / Docker 容器 / 新 VPS), 一条命令:
curl -fsSL https://gitee.com/weber-pan/ctrip-mcp/raw/master/bootstrap.sh | bash
```

`bootstrap.sh` 自动完成:
1. 探测 Python ≥ 3.10
2. `git clone` 到 `~/.ctrip-mcp/`
3. 创建 venv + `pip install -e .`
4. 探测/下载 Chromium (~150MB)
5. MCP 协议握手验证
6. **e2e 测试**:抓沙巴产品 64158367 + 解析 + 7/4 班期价
7. 打印**下游接入指引**(Claude Code / Hermes / mcphub)

最后输出:
```
✓ ctrip-mcp 安装完成
[Claude Code] 在项目根加 .mcp.json
[Hermes]       在 ~/.hermes/config.yaml 加
[mcphub]       Web UI 手动加 stdio server
```

---

## 1. 状态 Badge

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![MCP](https://img.shields.io/badge/MCP-2024--11--05-green)
![Chromium](https://img.shields.io/badge/chromium-required-orange)
![License: MIT](https://img.shields.io/badge/license-MIT-lightgrey)
![Tests](https://img.shields.io/badge/tests-e2e_pass-brightgreen)

## 2. 三层架构

```
┌────────────────────────────────────────────────────────────┐
│ AGENTS.md (Claude Code / Hermes 自动读)                     │
│ 5 工具表 + 踩坑日志 + city 字典 + URL 解析                  │
└────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────┐
│ skill/  (3 Agent skill + umbrella)                          │
│  ctrip-product-research/    路由 (user URL → 哪个子 skill)  │
│  ├─ ctrip-spa-capture/      技术层 (Playwright 真抓)        │
│  └─ ctrip-product-report/   工作流层 (11 段报告模板)        │
└────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────┐
│ src/ctrip_mcp/  (MCP server, stdio)                        │
│  5 工具: capture / get_product / compare / hotel / health   │
└────────────────────────────────────────────────────────────┘
                              ↑
        跨 MCP 客户端 (Claude Code / Hermes / mcphub)
```

## 3. 为什么需要这个仓库

| 路径 | 数据质量 | 风险 |
|---|---|---|
| 携程 PC/H5 `curl` | ❌ 403/404(纯 CSR 壳) | 拿不到任何数据 |
| wendao LLM 兜底(`xiecheng-mcp`) | ⭐⭐⭐ LLM 复述 | **串台**(问 p64158367 沙巴 → 给 p71068823 重庆) |
| **本仓库 Playwright 真抓** | ⭐⭐⭐⭐⭐ 真实 JSON | 需 chromium, 抓取约 25s/产品 |

**结论**:**双轨并用** — 优先本仓库(真抓), 失败/跨产品比对用 wendao 兜底。

## 4. 工具列表 (5 个 MCP Tools)

| 工具 | 说明 | 底层接口 |
|---|---|---|
| `ctrip_spa_capture` | 抓 m 端 h5 SPA 真实 graphql/soa body | Playwright + Chromium + fetch hook |
| `ctrip_get_product` | 解析 4 条线路/价格日历/酒店/点评 | 本地 JSON 解析 |
| `ctrip_compare_subproducts` | 对 4 个 sub-productId 各跑一次抓取 | `ctrip_spa_capture` 多次 |
| `ctrip_get_hotel_price` | 查某酒店 7/4-7/9 真实房型+价 | `AI_Go_Hotel_MCP` 适配 |
| `ctrip_health` | 健康检查 — Chromium 在不在、产物目录可写 | 本地 |

## 5. 端到端测试结果 (2026-06-06, 沙巴 64158367 + 印尼 69762187)

### 沙巴 4 线路

```
=== 1) ctrip_spa_capture ===
duration: 15.16s
xhrs count: 11
  saved getCommentSummary / getByRelationId / getPromotionTag
  saved ProductInfo_2nd_V3_h5 / VPC_SelectDateProductInfo_h5
  saved batchPriceCalendar / ProductInfo_VisaInfo_h5
  saved dom / screenshot

=== 2) ctrip_get_product ===
  name: 马来西亚沙巴 7 日 5 晚私家团
  min_price: ¥5763 (orig ¥5798) on 2026-06-24
  lines: 4
    - subId=64158367 sort=1  3+2 组合, 双酒店随心任选
    - subId=38789419 sort=2  高端升级--2 晚丹绒香格里拉
    - subId=73810124 sort=3  2 晚热销+3 晚海滨度假酒店
    - subId=73810123 sort=4  全程同酒店入住, 无需舟车劳顿
  hotels: 8
  comments: scoreAvg=4.8 count=1
  price_calendar dates: 252
    全月最低: 2026-09-07 ¥4849 (line 3+2 组合)

=== 3) 7/4 班期价 (4 条线) ===
  subId=64158367  ¥6857  3+2 组合
  subId=38789419  ¥8365  高端升级
  subId=73810124  ¥7360  2 晚热销+3 晚海滨
  subId=73810123  ¥6905  全程同酒店
```

### 印尼 69762187 单线路 (11 段补漏)

| 段 | 数据源 | 例子 |
|---|---|---|
| 价格日历 | `VPC.dailyMinPrices[]` | **207 天**, 落 CSV, 区间查询支持 |
| 7 段摘要 | `cardItems[]` | 行=飞机/住=5 晚 4 钻/团=不拼/游=16/餐=6 早 1 午 |
| 行程结构 | `SegmentInfo.Segments[]` | **10 段**: 上海→泗水→Kanigaran→Licin→巴厘岛→上海 |
| 可选酒店 | `imageHotelList[]` | 9 家带 hotelId (可调 hotelMCP) |
| 8 POI | `ImagePoiList[]` | 爪哇岛/罗威纳/水神庙/... |
| 68 城价 | `DepartureCityPriceList[]` | 上海 ¥7557 / 深圳 ¥6345 (最便宜) |
| 销量/流量 | `OrderPersonCount + VacationPersons` | 328 销 / 8636 月访问 |
| 8 竞品 | `MoreRecommendProductList[]` | 拼小团最便宜 ¥6412 |
| 4 类图片 | 15+ 张/产品 | DescriptionInfo/POI/PM/brand |
| 特殊费用 | `FeeInfoList` | 巴厘岛 15 万印尼盾旅游税 |
| 签证 | `Visa` | 落地签 35 美金/人 |

## 6. 接入 MCP 客户端

### [Claude Code](https://docs.anthropic.com/en/docs/claude-code)

仓库已带 `.mcp.json.example`, 复制为 `.mcp.json` 即生效:

```bash
cp .mcp.json.example .mcp.json
# 或在项目根直接:
claude  # Claude Code 自动读 .mcp.json
```

### [Hermes Agent](https://hermes-agent.nousresearch.com/docs)

```bash
# 一键注册为 skill
bash install-as-skill.sh
```

或手动加 `~/.hermes/config.yaml` (见 `docs/HERMES_CONFIG.yaml.example`):

```yaml
mcp_servers:
  - name: ctrip
    type: stdio
    command: /opt/hermes/.venv/bin/python
    args: [-m, ctrip_mcp.server]
    workdir: /opt/data/ctrip-mcp
```

### [mcphub](https://github.com/.../mcphub)

Web UI 手动加 1 个 stdio server:

| 字段 | 值 |
|---|---|
| Name | `ctrip` |
| Command | `/opt/hermes/.venv/bin/python` |
| Args | `-m ctrip_mcp.server` |
| Workdir | `/opt/data/ctrip-mcp` |

详见 [`docs/MCPHUB_INTEGRATION.md`](docs/MCPHUB_INTEGRATION.md)。

### 任何 stdio MCP 客户端

```bash
/opt/hermes/.venv/bin/python -m ctrip_mcp.server
```

## 7. city 字典 (国内出发城市 ID)

URL `?city=XX` 不是地区码, 是携程内部出发城市 ID:

| ID | 城市 | ID | 城市 |
|---|---|---|---|
| 1 | 北京 | 17 | 杭州 |
| 2 | **上海** | 28 | 成都 |
| 3 | 天津 | 30 | 深圳 |
| 5 | 哈尔滨 | 32 | 广州 |
| 12 | 南京 | 1244 | 重庆 |

完整 68 城在抓取后的 `DepartureCityPriceList[]` 里。

## 8. 关键 graphql 接口

| 接口 | 拿什么 |
|---|---|
| `ProductInfo_2nd_V3_h5` | 4 条线路 groupCard、8 家酒店、点评汇总、行程 |
| `VPC_SelectDateProductInfo_h5` | 4 个 sub-productId、7 月全月分价(252 天)、签证、班期规则 |
| `ProductInfo_VisaInfo_h5` | 签证详情 |
| `batchPriceCalendar` | 价格日历(优惠明细) |
| `getCommentSummary` | 真实用户点评分 |

**真实 endpoint**: `https://m.ctrip.com/restapi/soa2/18055/graphql?queryName=<MethodName>`

method 名在 `queryName=` query string 里 (URL 路径末尾是字面 "graphql")。

## 9. 文件清单 (本仓库)

```
ctrip-mcp/
├── AGENTS.md                          # ← Claude Code / Hermes 自动读
├── README.md                          # 本文件
├── CHANGELOG.md
├── bootstrap.sh                       # ← 一键 0 跑
├── install-as-skill.sh                # ← 注册为 Hermes skill
├── pyproject.toml                     # uv / pip install -e .
├── .env.example
├── .mcp.json.example                  # ← Claude Code 接入
├── .gitignore
├── src/ctrip_mcp/
│   ├── __init__.py
│   ├── server.py                      # 5 MCP 工具
│   └── capture.py                     # Playwright + fetch hook
├── scripts/
│   ├── test_server.py                 # 健康检查 + 工具列表
│   └── test_e2e.py                    # 抓沙巴 64158367 端到端
├── docs/
│   ├── MCPHUB_INTEGRATION.md          # mcphub 接入详细
│   └── HERMES_CONFIG.yaml.example     # Hermes config 片段
├── references/
│   ├── ctrip-spa-graphql-hook.md      # 抓取技术细节
│   └── hotels_mcp_ids.md              # 8 家沙巴酒店 hotelId
└── skill/                             # ← 3 Agent skill
    ├── ctrip-product-research/        # umbrella 路由
    ├── ctrip-spa-capture/             # 技术层
    └── ctrip-product-report/          # 工作流层
```

## 10. 与姊妹项目对比

| | ctrip-mcp (本仓库) | xiecheng-mcp |
|---|---|---|
| 数据源 | 携程 m 端 graphql | wendao LLM |
| 速度 | 15-25s/产品 | 10-30s/query |
| 准确度 | ⭐⭐⭐⭐⭐ 真实 JSON | ⭐⭐⭐ LLM 复述 |
| 串台风险 | ❌ 无 | ⚠️ 有 |
| 需要 token | ❌ | ✅ |
| 需要 chromium | ✅ (~150MB) | ❌ |
| 跨 MCP 客户端 | ✅ | ✅ |

**两个都装, 优先 ctrip-mcp(真抓), wendao 兜底**。

## 11. Pitfall 日志

- **Playwright `resp.text()` 拿不到 graphql body** — 用 `add_init_script` hook `window.fetch` + `XMLHttpRequest.send`
- **容器没 chrome 别再 `npx playwright install`** — 用 `~/.cache/ms-playwright/chromium-1223/chrome-linux64/chrome` 现成二进制
- **真抓要滚动到底部** — SPA lazy load, D3 之后不滚拿不到
- **`city=2` 是国内出发城市 ID** — 不是地区码, 完整字典见 §7
- **`Title` 在 2nd_V3 缺失** — 改查 `VPC.BasicInfo.Title`
- **POI 字段是 `imgUrl` 不是 `imageList`** — 之前 `p.get('poiName')` 写错过
- **feeInfoList.Description 字段不存在** — 真实数据在 `TargetPopulationItemList[].Description`
- **8/8 等日期价 ¥0** — 库存 0 或关闭班期, 过滤掉

详见 [`references/ctrip-spa-graphql-hook.md`](references/ctrip-spa-graphql-hook.md) 和 [`skill/ctrip-spa-capture/SKILL.md`](skill/ctrip-spa-capture/SKILL.md)。

## 12. License

MIT
