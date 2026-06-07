# ctrip-mcp

> 携程 m 端 h5 SPA → 5 个 MCP 工具, 真实 graphql JSON 落盘 (Playwright + Chromium)
> 不走 wendao LLM 兜底. 已知姊妹: xiecheng-mcp (LLM 兜底, 失败时用).

## 0. 60 秒从 0 跑

```bash
curl -fsSL https://gitee.com/weber-pan/ctrip-mcp/raw/master/bootstrap.sh | bash
```

`bootstrap.sh` 自动: clone → venv → pip → chromium (系统库缺则自动 `apt install`) → e2e 抓沙巴 64158367 → 打印接入指引.

## 1. 5 个 MCP 工具 (AI 必读)

调用协议: `JSON-RPC 2.0 over stdio`. mcphub 包装时所有 int/bool 可能被传成 string, **server 端已做容错** (`['string','integer']` schema).

| 工具 | 入参 | 出参 | 耗时 |
|---|---|---|---|
| `ctrip_spa_capture` | `product_id` (int, **必填**), `depart_city_id` (int, 默认 2=上海), `data_dir` (str, 默认 `/opt/data/ctrip-data`), `timeout` (int, 默认 60), `scroll` (bool, 默认 true) | 7 xhr JSON 落盘路径 + DOM txt + screenshot png + 11 xhr URL 列表 | ~17s |
| `ctrip_get_product` | `product_id` (int, **必填**), `data_dir` (str) | `product_basic` + `lines[4]` + `hotels[8]` + `comments` + `price_calendar[122天]` + `fee_summary` + `visa_summary` + `more_recommend[8]` | <1s (本地解析) |
| `ctrip_compare_subproducts` | `main_product_id` (int, **必填**), `sub_product_ids` (int[], **必填**, 4 个) | 4 sub-product 各跑一次 `ctrip_spa_capture` | ~70s (4×17s) |
| `ctrip_get_hotel_price` | (查 hotels_mcp_ids 文档) | 真实房型+价 | ~5s |
| `ctrip_health` | 无 | chromium 路径 / data_dir 可写 / playwright 可导入 | <1s |

### 调用顺序 (强约束)

```
ctrip_spa_capture  →  落盘 7 xhr JSON
                    ↓
ctrip_get_product   ←  读落盘的 ProductInfo_2nd_V3_h5.json
                    ↓
ctrip_compare_subproducts / ctrip_get_hotel_price
```

**不跑 capture 直接调 get_product 会返回** `❌ 未找到 ProductInfo_2nd_V3_h5 (pid=XXX)`.

## 2. 关键 graphql 接口 (5 个)

**base url**: `https://m.ctrip.com/restapi/soa2/18055/graphql?queryName=<MethodName>`

| queryName | 拿什么 |
|---|---|
| `ProductInfo_2nd_V3_h5` | **4 条线路 groupCard + 8 家酒店 + 点评汇总 + 行程 segments** ← 必抓 |
| `VPC_SelectDateProductInfo_h5` | 4 个 sub-productId + **122 天分价** + 签证 + 班期规则 |
| `ProductInfo_VisaInfo_h5` | 签证详情 |
| `batchPriceCalendar` | 价格日历 (优惠明细) |
| `getCommentSummary` | 真实用户点评分 |

**Spa URL 模板** (必须带 shoppingid 触发 graphql):

```
https://m.ctrip.com/webapp/vacations/tour/detail?productId=64158367&departCityId=2&shoppingid=677ec57391474056ab2291eee5c1ca45
```

## 3. 城市 ID 字典 (国内出发)

`?city=2` 是携程内部**出发城市 ID**, 不是地区码:

| ID | 城市 | ID | 城市 |
|---|---|---|---|
| 1 | 北京 | 17 | 杭州 |
| **2** | **上海** (默认) | 28 | 成都 |
| 3 | 天津 | 30 | 深圳 |
| 5 | 哈尔滨 | 32 | 广州 |
| 12 | 南京 | 1244 | 重庆 |

完整 68 城在抓取后的 `DepartureCityPriceList[]` 里.

## 4. 4 个 Agent skill (自动加载)

| Skill | 作用 |
|---|---|
| `ctrip-product-research` (umbrella) | 路由: user URL → 哪个子 skill |
| `ctrip-spa-capture` | 技术层 (Playwright 真抓) |
| `ctrip-product-report` | 工作流层 (11 段报告模板) |
| **`ctrip-product-decision-deck`** ✨ | **v4 决策手册 PPT** (2026-06-07 新, 25-28 页旅客视角) |

skill 调 `skill_view(name='ctrip-product-decision-deck')` 看完整 SKILL.md + run_v4.sh 用法.

## 5. Pitfall (AI 必读)

1. **必须有 `shoppingid` URL 参数** — 不带 → SPA 不触发 `getShoppingDetail` graphql → 0 xhr
2. **必须 `scroll=True`** — SPA lazy load, D3 之后不滚拿不到后段
3. **容器 chromium 缺系统库** — 装 `bash scripts/install_deps.sh` (apt 装 libnss3/libxkbcommon0 等 68 个包 + fonts-noto-cjk)
4. **mcphub 把 int/bool 传成 string** — schema 已声明 `['string','integer']` 兼容, server 强制转
5. **`Title` 在 2nd_V3 缺失** — 改查 `VPC.BasicInfo.Title`
6. **POI 字段是 `imgUrl`** 不是 `imageList`
7. **feeInfoList.Description 字段不存在** — 真实在 `TargetPopulationItemList[].Description`
8. **¥0 价格过滤掉** — 库存 0 或关闭班期
9. **`Agent loops`**: `page.on('response')` 抓不到时, 用 `page.expect_response()` 模式重抓
10. **不要替用户登录** — 拒绝收 cookie/手机号/验证码; `shoppingid` 是匿名询价凭证, 24-48h 失效, 不需登录

## 6. E2E 测试样例 (沙巴 64158367, 4 线)

```
=== 1) ctrip_spa_capture ===
duration: 17.24s, xhrs: 11
saved: getCommentSummary, getByRelationId, getPromotionTag, ProductInfo_2nd_V3_h5, VPC_SelectDateProductInfo_h5, batchPriceCalendar, ProductInfo_VisaInfo_h5, dom, screenshot

=== 2) ctrip_get_product ===
name: 马来西亚沙巴 7 日 5 晚私家团
min_price: ¥5762 (orig ¥5807) on 2026-06-24
lines: 4
  - subId=64158367 sort=1  3+2 组合, 双酒店随心任选
  - subId=38789419 sort=2  高端升级--2 晚丹绒香格里拉
  - subId=73810124 sort=3  2 晚热销+3 晚海滨度假酒店
  - subId=73810123 sort=4  全程同酒店入住, 无需舟车劳顿
hotels: 8 (莎利雅香格里拉/希尔顿/万豪/凯悦/凯悦尚萃/丹绒香格里拉/喜来登/艾美)
comments: scoreAvg=4.8 count=1
price_calendar dates: 122
  全月最低: 2026-09-07 ¥4849 (line 3+2 组合)

=== 3) 7/4 班期价 (4 条线) ===
  subId=64158367  ¥6,857  3+2 组合
  subId=38789419  ¥8,365  2 晚香格里拉
  subId=73810124  ¥7,355  2 晚热销+3 晚海滨
  subId=73810123  ¥6,905  全程同酒店 ← 最便宜
```

## 7. 仓库结构 (仅关键路径)

```
ctrip-mcp/
├── AGENTS.md                          # Claude Code / Hermes 自动读
├── bootstrap.sh                       # 0 跑 (curl | bash)
├── install-as-skill.sh
├── pyproject.toml
├── src/ctrip_mcp/
│   ├── server.py                      # 5 工具 MCP server (stdio)
│   └── capture.py                     # Playwright + fetch hook
├── scripts/
│   ├── test_e2e.py                    # 端到端
│   └── install_deps.sh                # apt 装 chromium 系统库
└── skill/                             # 4 Agent skill
    ├── ctrip-product-research/        # umbrella
    ├── ctrip-spa-capture/
    ├── ctrip-product-report/
    └── ctrip-product-decision-deck/   # v4 PPT
```

## 8. License

MIT
