# 🇨🇳 ctrip-mcp

<pre>
      __      _
 ____/ /_____(_)__
/ __/ __/ __/ / _ \/___/  ' \/ __/ _ \
\__/\__/_/ /_/ .__/   /_/_/_/\__/ .__/
            /_/                /_/
</pre>

**Real Ctrip tour data through MCP — Playwright-captured GraphQL, no LLM guessing.**

[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Python ≥ 3.10](https://img.shields.io/badge/python-≥3.10-blue)](pyproject.toml)
[![MCP 1.0+](https://img.shields.io/badge/MCP-1.0+-purple)](https://modelcontextprotocol.io)
[![5 ctrip + 4 xhs tools](https://img.shields.io/badge/tools-9-orange)](#the-nine-mcp-tools)

`ctrip-mcp` opens a real Chromium against Ctrip's mobile h5 SPA, captures
the live GraphQL responses (`ProductInfo_2nd_V3_h5`,
`VPC_SelectDateProductInfo_h5`, `batchPriceCalendar`, …), and parses them
deterministically into 4 sub-product lines, a 122-day price calendar,
8 hotels, real user comments and visa info. The server also bundles
[xiaohongshu](https://www.xiaohongshu.com) tools (`xhs_search_notes`,
`xhs_explore`, `xhs_get_note_content`, `xhs_health`) for traveller POV
research — both surfaces exposed as **nine stdio MCP tools**. No login,
no cookie scraping, no LLM hallucination for prices.

> **Note:** Ctrip capture uses a transient anonymous `shoppingid` token
> (24-48h TTL). It does **not** log in, does **not** request phone
> numbers, SMS codes, or cookies, and the server-side input validator
> **refuses** any such input. The `xhs_*` tools require a valid
> `REDNOTE_COOKIES` env var to be set; without it they are hidden from
> the tool list.

## What you get

Sample output of `ctrip_get_product` for `product_id=64158367`
(Malaysia · Sabah · 7 days 5 nights private tour):

```json
{
  "name": "马来西亚沙巴 7 日 5 晚私家团",
  "min_price": { "amount": 5762, "original": 5807, "date": "2026-06-24" },
  "lines": [
    { "sub_id": 64158367, "sort": 1, "name": "3+2 组合, 双酒店随心任选", "price": 6857 },
    { "sub_id": 38789419, "sort": 2, "name": "升级 2 晚丹绒香格里拉",     "price": 8365 },
    { "sub_id": 73810124, "sort": 3, "name": "2 晚热销 + 3 晚海滨度假",   "price": 7355 },
    { "sub_id": 73810123, "sort": 4, "name": "全程同酒店入住",            "price": 6905 }
  ],
  "hotels": ["莎利雅香格里拉", "希尔顿", "万豪", "凯悦", "凯悦尚萃",
             "丹绒香格里拉", "喜来登", "艾美"],
  "price_calendar": { "days": 122, "month_low": { "date": "2026-09-07", "amount": 4849 } },
  "comments": { "score_avg": 4.8, "count": 1 }
}
```

## Why ctrip-mcp?

Most LLM agents try to "read the Ctrip page" to answer price questions.
That approach fails in three predictable ways:

- **Tool-precise capture** — Playwright + `page.expect_response()` hooks
  the exact 11 XHR calls; nothing is scraped from visible text.
- **Multi-step reasoning built in** — `ctrip_spa_capture` (write 7
  JSONs to disk) → `ctrip_get_product` (parse) → `ctrip_compare_subproducts`
  (run capture 4× in parallel branches). The order is enforced by the
  server, not by the agent's prompt.
- **Real-world messiness handled** — stringified ints from mcphub,
  `Title` living in `VPC.BasicInfo` not `ProductInfo_2nd_V3_h5`, `¥0`
  rows for closed dates, scroll-required SPA lazy-load. All encoded as
  fallbacks in the parser, not as agent heuristics.
- **Practical outcomes** — output is structured JSON you can pipe into
  a report generator, a PPT decision deck (`ctrip-product-decision-deck`
  skill), or a hotel-price comparison. Not a sentence to be re-parsed
  by another LLM.

## Quick start

```bash
# One-liner install (clones, builds venv, installs Chromium, runs e2e)
curl -fsSL https://github.com/weber-pan/ctrip-mcp/raw/master/bootstrap.sh | bash
```

`bootstrap.sh` handles: Python ≥ 3.10 check → `git clone` into
`~/.ctrip-mcp` → venv → `pip install -e .` → Chromium + 68 system
apt packages → e2e capture of Sabah `64158367` → prints mcphub /
Claude Code / Hermes wiring snippets. Re-running is safe; an existing
clone is `git pull`ed first.

**Requirements:** Python 3.10+, ~600 MB disk (Chromium + caches),
apt access for system libs (the installer runs `apt-get install` on
Debian/Ubuntu; macOS uses the system Chromium).

**Optional — xhs tools:** set `REDNOTE_COOKIES` (paste from browser
DevTools) in the MCP server env to expose the 4 `xhs_*` tools. Without
it, only the 5 `ctrip_*` tools are visible.

## The nine MCP tools

Transport: **JSON-RPC 2.0 over stdio.** When wrapped by mcphub, integer
and boolean args may arrive as strings; the server tolerates both
(schema declares `['string', 'integer']`).

| Tool | Required | Optional | Output | Latency |
|---|---|---|---|---|
| `ctrip_spa_capture` | `product_id` (int) | `depart_city_id` (int, default `2`), `data_dir` (str), `timeout` (int, default `60`), `scroll` (bool, default `true`) | 7 GraphQL JSONs on disk + DOM txt + screenshot png + 11 XHR URL list | ~17 s |
| `ctrip_get_product` | `product_id` (int) | `data_dir` (str) | `product_basic` + `lines[4]` + `hotels[8]` + `comments` + `price_calendar[122d]` + `fee_summary` + `visa_summary` + `more_recommend[8]` | <1 s (local parse) |
| `ctrip_compare_subproducts` | `main_product_id` (int), `sub_product_ids` (int[4]) | — | Each sub-product's full `ctrip_get_product` payload | ~70 s (4 × 17 s) |
| `ctrip_get_hotel_price` | `hotel_id` (int) | `check_in`, `check_out` | Real room types + nightly price via AI_Go_Hotel_MCP | ~5 s |
| `ctrip_health` | — | — | Chromium path, `data_dir` writable, Playwright importable | <1 s |
| `xhs_search_notes` | `keyword` (str) | `limit` (int) | Xiaohongshu search results | <1 s |
| `xhs_explore` | — | `limit` (int) | Xiaohongshu explore feed | <1 s |
| `xhs_get_note_content` | `note_id` (str) | — | Note text + media URLs | <1 s |
| `xhs_health` | — | — | Xiaohongshu module health (cookie present? expired?) | <1 s |

**Call order is strict** for Ctrip — calling `ctrip_get_product` before
`ctrip_spa_capture` returns `❌ ProductInfo_2nd_V3_h5 not found`.

## The five key GraphQL endpoints

Base URL: `https://m.ctrip.com/restapi/soa2/18055/graphql?queryName=<Method>`

| `queryName` | Returns |
|---|---|
| `ProductInfo_2nd_V3_h5` | **4 sub-product lines + 8 hotels + comment summary + segments** — required |
| `VPC_SelectDateProductInfo_h5` | 4 sub-productIds + **122-day price matrix** + visa + calendar rules |
| `ProductInfo_VisaInfo_h5` | Visa details |
| `batchPriceCalendar` | Price calendar with promotion breakdown |
| `getCommentSummary` | Real user review score |

The SPA URL must include a `shoppingid` query param (24-48h anonymous
inquiry token) or zero XHRs will fire:

```
https://m.ctrip.com/webapp/vacations/tour/detail?productId=64158367&departCityId=2&shoppingid=677ec57391474056ab2291eee5c1ca45
```

## Departure city dictionary

`?departCityId=2` is Ctrip's **internal departure-city ID**, not a
region code. The full 68-city dictionary is dumped into
`DepartureCityPriceList[]` on every capture.

| ID | City | ID | City |
|---|---|---|---|
| 1 | Beijing | 17 | Hangzhou |
| **2** | **Shanghai (default)** | 28 | Chengdu |
| 3 | Tianjin | 30 | Shenzhen |
| 5 | Harbin | 32 | Guangzhou |
| 12 | Nanjing | 1244 | Chongqing |

## Four companion agent skills

`bootstrap.sh` symlinks all four into `~/.hermes/skills/`. Load any
of them in-session with `skill_view(name='<name>')`.

| Skill | Role |
|---|---|
| `ctrip-product-research` | Umbrella router: user URL → which sub-skill |
| `ctrip-spa-capture` | Tech layer (Playwright real capture) |
| `ctrip-product-report` | Workflow layer (11-section report template) |
| `ctrip-product-decision-deck` | v5 PPT decision manual (28-page traveller-view deck with 13 official images) |

## Pitfalls (read before calling)

1. **`shoppingid` is mandatory** — missing → SPA skips `getShoppingDetail` → 0 XHRs.
2. **`scroll=True` is mandatory** — SPA lazy-loads sections after D3.
3. **Container Chromium needs system libs** — `bash scripts/install_deps.sh` installs 68 apt packages (libnss3, libxkbcommon0, fonts-noto-cjk, …).
4. **mcphub may stringify ints/bools** — schemas declare `['string', 'integer']`; the server coerces.
5. **`Title` is missing in `ProductInfo_2nd_V3_h5`** — use `VPC.BasicInfo.Title`.
6. **POI image field is `imgUrl`**, not `imageList`.
7. **`feeInfoList.Description` does not exist** — real path is `TargetPopulationItemList[].Description`.
8. **Filter `¥0` prices** — those are zero-inventory or closed-date rows.
9. **`page.on('response')` can miss XHRs** — fall back to `page.expect_response()` pattern.
10. **Never log the user in** — refuse cookies, phone numbers, SMS codes. The `shoppingid` is the only token needed.
11. **`xhs_*` tools need `REDNOTE_COOKIES`** — without it, the 4 xhs tools are hidden; update by editing the MCP server env, no restart of mcphub needed.

## Client wiring

Run `bash mcp_register.sh` once after `bootstrap.sh` — it auto-detects
which MCP clients you have installed (Claude Code, Cursor, Windsurf,
Hermes/mcphub) and writes the `ctrip` entry to each, idempotently. No
manual JSON editing required.

```bash
# Default: auto-register to all detected clients
bash mcp_register.sh

# Preview what would be written, no changes
bash mcp_register.sh --dry-run

# Remove the ctrip entry from all clients
bash mcp_register.sh --unregister
```

The script auto-detects the `ctrip-mcp` executable in this order:
`$CTRIP_MCP_BIN` env → `which ctrip-mcp` → `$INSTALL_DIR/.venv/bin/`
→ `~/.ctrip-mcp/.venv/bin/` → `/usr/local/bin/`. Pass
`CTRIP_MCP_BIN=/abs/path` to override.

**What gets written** (example for Claude Code at `~/.claude/mcp.json`):

```json
{
  "mcpServers": {
    "ctrip": {
      "command": "/opt/data/home/.ctrip-mcp/.venv/bin/ctrip-mcp",
      "env": {
        "CTRIP_DATA_DIR": "/opt/data/ctrip-data"
      }
    }
  }
}
```

**After registration, restart your MCP client** (Claude Code / Cursor
/ Windsurf) to pick up the new server. Hermes/mcphub does not need a
restart — it picks up the new entry on the next config reload.

### Manual wiring (if you don't want to run `mcp_register.sh`)

| Client | Config file | Entry |
|---|---|---|
| **Claude Code** | `~/.claude/mcp.json` | `{ "mcpServers": { "ctrip": { "command": "<abs-path-to-ctrip-mcp>" } } }` |
| **Hermes / mcphub** | `mcp_servers.yaml` | `- name: ctrip`<br>`  command: <abs-path-to-ctrip-mcp>` |
| **Cursor / Windsurf / Aider** | stdio transport | works out of the box |

> **Pitfall:** the `ctrip-mcp` command only exists inside the
> `~/.ctrip-mcp/.venv/bin/` directory after `bootstrap.sh` — it is
> **not** on `$PATH` by default. Use the absolute path in your config,
> or symlink it: `ln -sf ~/.ctrip-mcp/.venv/bin/ctrip-mcp /usr/local/bin/ctrip-mcp`.

## Command reference

| Flag / env | Default | Notes |
|---|---|---|
| `CTRIP_DATA_DIR` | `/opt/data/ctrip-data` | Where 7 GraphQL JSONs and screenshots are written. Must be writable. |
| `CTRIP_DEPART_CITY_ID` | `2` | Shanghai. Override per-call via `ctrip_spa_capture` arg. |
| `CTRIP_TIMEOUT` | `60` | Seconds before a capture times out. |
| `CTRIP_NO_SCROLL` | `false` | Set `1` to skip the lazy-load scroll (not recommended; you lose back-half lines). |
| `REDNOTE_COOKIES` | _(unset)_ | Browser cookie string for xhs tools. Format: `a1=xxx; web_session=yyy; …` |
| `REDNOTE_COOKIES_FILE` | _(unset)_ | Alt: path to a cookies file. `REDNOTE_COOKIES` takes precedence. |

## Repository layout

```
ctrip-mcp/
├── AGENTS.md                          # auto-read by Claude Code / Hermes / Codex / Aider
├── bootstrap.sh                       # one-liner installer
├── mcp_register.sh                    # auto-register ctrip to Claude/Cursor/Windsurf/mcphub
├── install-as-skill.sh                # symlinks skills into ~/.hermes/skills/
├── pyproject.toml
├── src/
│   ├── ctrip_mcp/
│   │   ├── server.py                  # 5 MCP tools (stdio)
│   │   └── capture.py                 # Playwright + fetch hook
│   └── rednote_mcp/                   # bundled xiaohongshu sister tools (4 tools)
├── scripts/
│   ├── test_e2e.py
│   └── install_deps.sh                # apt-get install chromium system libs
└── skill/                             # 4 agent skills
    ├── ctrip-product-research/        # umbrella
    ├── ctrip-spa-capture/
    ├── ctrip-product-report/
    └── ctrip-product-decision-deck/   # v5 PPT
```

## License

[MIT](LICENSE)
