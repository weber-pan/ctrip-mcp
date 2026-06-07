# AGENTS.md

This file tells AI coding agents (Claude Code, Codex, Aider, Hermes, etc.) how to use this project.

## What this is

`ctrip-mcp` is a Model Context Protocol (MCP) server that lets any MCP-compatible AI agent
**directly fetch real travel product data from Ctrip's mobile H5 SPA** — not via LLM
summarization (which can hallucinate), but by running Playwright + Chromium and intercepting
the actual `graphql` API responses that Ctrip's own mobile app uses.

## Quick start

If you are an AI agent and your user gives you a Ctrip product URL like
`https://vacations.ctrip.com/travel/detail/p64158367/?city=2&rv=1`, the workflow is:

1. **Read this AGENTS.md to the end.**
2. **Verify installation** by running `python scripts/test_server.py`.
3. **If not installed**: run `bash bootstrap.sh` (handles venv + pip + chromium).
4. **Use the 5 tools** (see "Tools" section below).
5. **Read `skill/ctrip-product-research/SKILL.md`** for the higher-level workflow.

## Tools

| Tool | What it does |
|------|--------------|
| `ctrip_spa_capture` | Fetch the product's real graphql JSON via Playwright (≈25s). |
| `ctrip_get_product` | Parse the captured JSON into structured product data. |
| `ctrip_compare_subproducts` | Re-run capture for each sub-productId (for 4-line products). |
| `ctrip_get_hotel_price` | Fetch real hotel prices for one of the in-route hotels. |
| `ctrip_health` | Health check — chromium, output dir, last capture timestamp. |
| `xhs_search_notes` | 小红书关键词搜索 (有 cookie 才暴露, 见下方)。 |
| `xhs_explore` | 小红书首页推荐 feed (有 cookie 才暴露)。 |
| `xhs_get_note_content` | 拿小红书笔记正文 (有 cookie 才暴露)。 |
| `xhs_health` | 小红书模块健康 (有 cookie 才暴露)。 |

## Cookie 注入 (小红书)

ctrip-mcp 内嵌 rednote-mcp, **有 cookie 才有 xhs_* tool**。

```yaml
# mcphub Add Server 时配 env (推荐):
env:
  REDNOTE_COOKIES: 'a1=xxx; web_session=yyy; abRequestId=zzz; ...'
```

**DevTools 怎么复制**: `web.xiaohongshu.com` → F12 → Application → Cookies → `.xiaohongshu.com` → 全选 → **Ctrl+C 直接粘贴到 mcphub env**。兼容两种格式:
- `name=value; name2=value2` (Ctrl+C 直贴)
- `[{"name":"a1","value":"xxx"}, ...]` (右键 Copy as JSON)

或者用文件路径 (向后兼容):
```yaml
env:
  REDNOTE_COOKIES_FILE: "/app/.secrets/xhs_cookies.json"
```

cookie 获取: 浏览器登录 `web.xiaohongshu.com` → DevTools → Application → Cookies → .xiaohongshu.com → 全选复制 JSON。

**更新流程**: mcphub 面板 → 改 `REDNOTE_COOKIES` env → 重启服务 → 新 cookie 自动生效。不需要容器挂载、不需要文件路径。

没配 cookie → ctrip-mcp 只暴露 5 个 ctrip_* tool, xhs_* 不可见。

## Pitfalls (read these)

- **Ctrip URLs are server-rendered shells + CSR JSON.** Plain `curl` returns 403. You must
  use the Playwright capture path. Don't try to scrape the DOM with regex.
- **Chromium is required.** If `~/.cache/ms-playwright/chromium-1223/chrome-linux64/chrome`
  doesn't exist, `bootstrap.sh` downloads it (~150MB). Don't `npx playwright install`
  inside a Docker container — it will fail.
- **`city=` is a Ctrip-internal departure-city ID, not a region code.** 1=Beijing, 2=Shanghai,
  3=Tianjin, 17=Hangzhou, 28=Chengdu, 30=Shenzhen, 32=Guangzhou, 1244=Chongqing. The full
  68-city dictionary appears in the captured `DepartureCityPriceList[]`.
- **Product with 1 line vs. 4 lines** — Some products have `groupCard.cards[]` with
  multiple sub-productIds (4 lines: standard / upgrade / hot / same-hotel). Others have
  just 1. Look at `len(cards)` first.
- **`Title` is missing in `ProductInfo_2nd_V3_h5`** — it's in
  `VPC_SelectDateProductInfo_h5.BasicInfo.Title`. Always use VPC for the product name.
- **Don't trust `wendao` LLM for 远期 (7/4) weather** — knowledge cutoff is 2026-01.
  Use `amap-mcp-maps_weather` for ≤4 days, and warn the user that anything beyond is
  LLM-prediction.

## Tests

```bash
# Tool + health check
python scripts/test_server.py

# End-to-end: capture 沙巴 64158367 + parse + 7/4 prices (~30s)
python scripts/test_e2e.py
```

## Output structure

Captures land in `${CTRIP_DATA_DIR:-/opt/data/ctrip-data}/`:

```
xhr_ProductInfo_2nd_V3_h5.json       # main product (34 fields)
xhr_VPC_SelectDateProductInfo_h5.json # VPC (16 fields: 行程 10 段, 销量, 68 城价)
xhr_getCommentSummary.json            # 真实用户点评
xhr_getByRelationId.json              # 关联产品
xhr_getPromotionTag.json              # 促销标签
xhr_batchPriceCalendar.json           # 价格日历明细
xhr_ProductInfo_VisaInfo_h5.json      # 签证
dom_text.txt                          # 整页 DOM 文本 (含 D1-D7 行程兜底)
```

After capture, run `python /opt/data/skills/devops/ctrip-spa-capture/scripts/extract_more.py <pid>`
to get a CSV of the 207-day price calendar + 4 image sources + 11段补漏.

## Skill integration

This project ships with **four** Agent skills under `skill/`:

- `skill/ctrip-product-research/` — umbrella / router
- `skill/ctrip-spa-capture/` — technical layer (Playwright + graphql)
- `skill/ctrip-product-report/` — 11-段 report template
- `skill/ctrip-product-decision-deck/` — **v5 决策手册 PPT**(2026-06-07 升级, p69762187 + p69852382 落地)
  - 4 出行 + 4 风格字段确认(8 Confirmations)
  - shoppingid + getShoppingDetail 抓 5 段真实酒店 + 航班
  - ctrip_dom_7days.py 抓图文行程 DOM(7 日 D1-D7 + 违约条款 + 6 早餐 1 午餐)
  - 28 页 SVG(editorial 杂志风 + 海岛蓝绿 + 火山橙红 + 真图嵌)
  - **v3 增量(必走)**: 13 张官方图嵌入(10 POI + 3 酒店) + P26-P28 三张图集页
  - **v5 升级**: 4 线 7/4-7/10 价格矩阵 + 4 沙巴 1 印尼 双案例 + lessons-failures-bank.md 守则
  - 升级脚本 `scripts/run_v4.sh` 端到端跑(4 出行参数预填)

Hermes agents can `skill_view(name='ctrip-spa-capture')` to load them.

## License

MIT
