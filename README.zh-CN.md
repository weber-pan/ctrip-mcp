# 🇨🇳 ctrip-mcp

<pre>
      __      _
 ____/ /_____(_)__
/ __/ __/ __/ / _ \/___/  ' \/ __/ _ \
\__/\__/_/ /_/ .__/   /_/_/_/\__/ .__/
            /_/                /_/
</pre>

**真实携程跟团游数据,走 MCP 协议 — Playwright 真抓 GraphQL,零 LLM 串台。**

[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Python ≥ 3.10](https://img.shields.io/badge/python-≥3.10-blue)](pyproject.toml)
[![MCP 1.0+](https://img.shields.io/badge/MCP-1.0+-purple)](https://modelcontextprotocol.io)
[![5 ctrip + 4 xhs 工具](https://img.shields.io/badge/tools-9-orange)](#九个-mcp-工具)

`ctrip-mcp` 用真 Chromium 打开携程 m 端 h5 SPA,抓 `ProductInfo_2nd_V3_h5`、
`VPC_SelectDateProductInfo_h5`、`batchPriceCalendar` 等 5 个 GraphQL 接口的真实响应,
确定性解析为 4 条线路、122 天价格、8 家酒店、真实点评、签证信息。Server **同进程**
打包了小红书工具(`xhs_search_notes` / `xhs_explore` / `xhs_get_note_content` /
`xhs_health`)做旅客视角调研,共 **9 个 stdio MCP 工具**。**不登录、不收 cookie、不靠
LLM 兜底价格**。

> **Note:** 携程抓取用临时匿名 `shoppingid` 凭证(24-48h TTL),不登录、不收手机号、
> 不收短信码,server 端输入校验**拒绝**任何这类输入。`xhs_*` 工具需要
> `REDNOTE_COOKIES` 环境变量才能暴露;没配的话 4 个 xhs 工具不会出现在 tool 列表里。

## 输出长这样

`ctrip_get_product` 拿 `product_id=64158367`(马来西亚沙巴 7 日 5 晚私家团):

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

## 为什么做这个

多数 LLM agent 试图"读携程页面"答价格题。这种做法必败在三个地方:

- **工具级精确抓取** — Playwright + `page.expect_response()` 钩住 11 个 XHR,不靠可见文本正则抠。
- **多步推理内建在 server** — `ctrip_spa_capture`(写 7 JSON 落盘)→ `ctrip_get_product`(解析)→
  `ctrip_compare_subproducts`(4 条线并行分支跑 capture)。调用顺序 server 强制,不是 agent 自我约束。
- **真实世界脏数据 server 兜住** — mcphub 把 int 传成 string、`Title` 在 `VPC.BasicInfo` 不在
  `ProductInfo_2nd_V3_h5`、`¥0` 是关闭班期、SPA 懒加载必须滚。全部硬编码在解析器里,不是 agent 心智。
- **产出可落地** — 输出是结构化 JSON,可直接灌进报告生成器、PPT 决策手册
  (`ctrip-product-decision-deck` skill)、酒店比价表。不是一句话让另一个 LLM 再解析一遍。

## 60秒上手

```bash
# 一行安装(克隆、venv、装 Chromium、跑 e2e)
curl -fsSL https://github.com/weber-pan/ctrip-mcp/raw/master/bootstrap.sh | bash
```

`bootstrap.sh` 流程:Python ≥ 3.10 探测 → `git clone` 到 `~/.ctrip-mcp` → venv →
`pip install -e .` → Chromium + 68 个系统 apt 包 → e2e 抓沙巴 `64158367` →
打印 mcphub / Claude Code / Hermes 接入片段。重跑安全:已存在则 `git pull`。

**依赖**:Python 3.10+、~600MB 磁盘(Chromium + 缓存)、apt 权限
(Debian/Ubuntu 跑 `apt-get install`;macOS 用系统 Chromium)。

**可选 — xhs 工具**:在 MCP server env 配 `REDNOTE_COOKIES`(从浏览器 DevTools 直接复制),
即可暴露 4 个 `xhs_*` 工具。不配就只有 5 个 `ctrip_*`。

## 九个 MCP 工具

**JSON-RPC 2.0 over stdio** 传输。mcphub 包装时 int/bool 可能传成 string,server 端
schema 同时声明 `['string', 'integer']` 兼容。

| 工具 | 必填 | 选填 | 输出 | 耗时 |
|---|---|---|---|---|
| `ctrip_spa_capture` | `product_id` (int) | `depart_city_id` (int,默认 `2`)、`data_dir` (str)、`timeout` (int,默认 `60`)、`scroll` (bool,默认 `true`) | 7 个 GraphQL JSON 落盘 + DOM txt + screenshot png + 11 XHR URL | ~17s |
| `ctrip_get_product` | `product_id` (int) | `data_dir` (str) | `product_basic` + `lines[4]` + `hotels[8]` + `comments` + `price_calendar[122天]` + `fee_summary` + `visa_summary` + `more_recommend[8]` | <1s(本地解析) |
| `ctrip_compare_subproducts` | `main_product_id` (int)、`sub_product_ids` (int[4]) | — | 每个 sub-product 的完整 `ctrip_get_product` 载荷 | ~70s(4×17s) |
| `ctrip_get_hotel_price` | `hotel_id` (int) | `check_in`、`check_out` | 真实房型 + 晚均价(走 AI_Go_Hotel_MCP) | ~5s |
| `ctrip_health` | — | — | chromium 路径 / data_dir 可写 / playwright 可导入 | <1s |
| `xhs_search_notes` | `keyword` (str) | `limit` (int) | 小红书关键词搜索结果 | <1s |
| `xhs_explore` | — | `limit` (int) | 小红书首页推荐 feed | <1s |
| `xhs_get_note_content` | `note_id` (str) | — | 笔记正文 + 媒体 URL | <1s |
| `xhs_health` | — | — | 小红书模块健康(cookie 在/过期?) | <1s |

**携程调用顺序强约束** —— `ctrip_get_product` 在 `ctrip_spa_capture` 之前调会返回
`❌ ProductInfo_2nd_V3_h5 未找到`。

## 5 个核心 GraphQL 接口

**Base URL**: `https://m.ctrip.com/restapi/soa2/18055/graphql?queryName=<Method>`

| `queryName` | 拿到什么 |
|---|---|
| `ProductInfo_2nd_V3_h5` | **4 条线路 + 8 家酒店 + 点评汇总 + 行程 segments** ← 必抓 |
| `VPC_SelectDateProductInfo_h5` | 4 个 sub-productId + **122 天分价** + 签证 + 班期规则 |
| `ProductInfo_VisaInfo_h5` | 签证详情 |
| `batchPriceCalendar` | 价格日历(优惠明细) |
| `getCommentSummary` | 真实用户点评分 |

**SPA URL 必须带 `shoppingid`**(24-48h 匿名询价凭证,否则 0 个 XHR):

```
https://m.ctrip.com/webapp/vacations/tour/detail?productId=64158367&departCityId=2&shoppingid=677ec57391474056ab2291eee5c1ca45
```

## 出发城市 ID 字典

`?departCityId=2` 是携程**内部出发城市 ID**,不是地区码。完整 68 城字典在每次抓取
的 `DepartureCityPriceList[]` 里。

| ID | 城市 | ID | 城市 |
|---|---|---|---|
| 1 | 北京 | 17 | 杭州 |
| **2** | **上海(默认)** | 28 | 成都 |
| 3 | 天津 | 30 | 深圳 |
| 5 | 哈尔滨 | 32 | 广州 |
| 12 | 南京 | 1244 | 重庆 |

## 4 个配套 Agent skill

`bootstrap.sh` 自动把 4 个 skill 软链到 `~/.hermes/skills/`。session 内
`skill_view(name='<name>')` 加载。

| Skill | 作用 |
|---|---|
| `ctrip-product-research` | umbrella 路由:user URL → 哪个子 skill |
| `ctrip-spa-capture` | 技术层(Playwright 真抓) |
| `ctrip-product-report` | 工作流层(11 段报告模板) |
| `ctrip-product-decision-deck` | v5 PPT 决策手册(28 页旅客视角 + 13 张官方图) |

## 坑日志(调用前必读)

1. **`shoppingid` 必带** —— 不带 → SPA 不触发 `getShoppingDetail` → 0 个 XHR
2. **`scroll=True` 必带** —— SPA 懒加载,D3 之后不滚拿不到后段
3. **容器 chromium 缺系统库** —— 跑 `bash scripts/install_deps.sh`(apt 装 68 个包 + fonts-noto-cjk)
4. **mcphub 把 int/bool 传成 string** —— schema 已声明 `['string', 'integer']` 兼容
5. **`Title` 在 `ProductInfo_2nd_V3_h5` 缺失** —— 改查 `VPC.BasicInfo.Title`
6. **POI 字段是 `imgUrl`**,不是 `imageList`
7. **`feeInfoList.Description` 字段不存在** —— 真实路径 `TargetPopulationItemList[].Description`
8. **¥0 价格过滤掉** —— 库存 0 或关闭班期
9. **`page.on('response')` 抓不到 XHR** —— 用 `page.expect_response()` 模式重抓
10. **不要替用户登录** —— 拒绝收 cookie/手机号/验证码;`shoppingid` 是唯一凭证
11. **`xhs_*` 工具需要 `REDNOTE_COOKIES`** —— 不配 4 个 xhs 工具隐藏;改 MCP server env 即生效,不用重启 mcphub

## 客户端接入

跑完 `bootstrap.sh` 之后,**执行一次** `bash mcp_register.sh` —— 它会自动探
Claude Code / Cursor / Windsurf / Hermes-mcphub 哪个客户端装了,然后把
`ctrip` entry 写进去,**幂等**,不用手改 JSON。

```bash
# 默认: 注册到所有检测到的客户端
bash mcp_register.sh

# 只看会写什么, 不真改
bash mcp_register.sh --dry-run

# 从所有客户端删除 ctrip entry
bash mcp_register.sh --unregister
```

**自动找可执行** 顺序:`$CTRIP_MCP_BIN` env → `which ctrip-mcp` →
`$INSTALL_DIR/.venv/bin/` → `~/.ctrip-mcp/.venv/bin/` →
`/usr/local/bin/`。`CTRIP_MCP_BIN=/abs/path bash mcp_register.sh`
可手动覆盖。

**写入长这样** (Claude Code `~/.claude/mcp.json` 示例):

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

**想用短形式 `ctrip-mcp`**(全局 PATH 可用),做个软链:

```bash
ln -sf ~/.ctrip-mcp/.venv/bin/ctrip-mcp /usr/local/bin/ctrip-mcp
```

之后配置文件可以**原样**写:

```json
{
  "mcpServers": {
    "ctrip": {
      "command": "ctrip-mcp",
      "env": {
        "CTRIP_DATA_DIR": "/opt/data/ctrip-data"
      }
    }
  }
}
```

## 小红书 (XHS) cookie

`ctrip-mcp` 总共 **9 个工具** —— 5 个旅行工具 (`ctrip_*`) 加 4 个小红书姊妹
工具 (`xhs_*`)。**4 个 `xhs_*` 工具只在 `REDNOTE_COOKIES_FILE` 指向一个可读
JSON 文件时才出现在 `tools/list`**,没配就只剩 5 个。

| 工具族 | 数量 | 需 cookie | 工具名 |
|---|---|---|---|
| `ctrip_*` (携程) | 5 | 不需要 | `ctrip_spa_capture`、`ctrip_get_product`、`ctrip_compare_subproducts`、`ctrip_get_hotel_price`、`ctrip_health` |
| `xhs_*` (小红书) | 4 | **需要** | `xhs_search_notes`、`xhs_explore`、`xhs_get_note_content`、`xhs_health` |

**cookie 注入优先级**:

1. `REDNOTE_COOKIES` env —— 原始 cookie 字符串,请求时解析
2. `REDNOTE_COOKIES_FILE` env —— JSON 文件路径,启动时读取
3. 都没配 → `xhs_*` 调用返回"请配置我"错误

**怎么抓 cookie** (Chrome DevTools, 30 秒):

1. Chrome 打开 <https://www.xiaohongshu.com>,登录
2. `F12` → **Application** → **Cookies** → `https://www.xiaohongshu.com`
3. 全选行 → 右键 **Copy** → 粘成 JSON 数组
4. 存成 `/opt/data/.secrets/xhs_cookies.json`(路径随便)

```json
[
  {"name": "a1", "value": "xxx", "domain": ".xiaohongshu.com", "path": "/"},
  {"name": "web_session", "value": "yyy", "domain": ".xiaohongshu.com", "path": "/"},
  {"name": "webId", "value": "zzz", "domain": ".xiaohongshu.com", "path": "/"}
]
```

加到 MCP 配置里:

```json
{
  "mcpServers": {
    "ctrip": {
      "command": "ctrip-mcp",
      "env": {
        "CTRIP_DATA_DIR": "/opt/data/ctrip-data",
        "REDNOTE_COOKIES_FILE": "/opt/data/.secrets/xhs_cookies.json"
      }
    }
  }
}
```

> **为啥用文件而不是 env 直配?** `REDNOTE_COOKIES_FILE` 控制 4 个
> `xhs_*` 工具**是否在 `tools/list` 中列出**。`REDNOTE_COOKIES` env 只
> 在**实际请求**时才生效 —— 配了它工具能跑但 MCP 客户端看不见工具列表。
> **想 9 工具全亮,必须配 `REDNOTE_COOKIES_FILE`**。

> **安全提示**:cookie 等于完整账号权限,**别提交到 git**、**别往共享
> 聊天里贴**。泄露了立即在小红书该设备**退出 → 重登 → 重新抓**。

> **过期**:小红书 cookie 一般 1-2 周失效。`xhs_*` 工具开始返回空数据
> 或登录报错时,重新抓一次。

**注册完记得重启 MCP 客户端** (Claude Code / Cursor / Windsurf)。
Hermes/mcphub **不用重启**,改完 env 配置下次 reload 自动生效。

### 手动接入(不想跑 `mcp_register.sh`)

| 客户端 | 配置文件 | 入口 |
|---|---|---|
| **Claude Code** | `~/.claude/mcp.json` | `{ "mcpServers": { "ctrip": { "command": "<abs-path-to-ctrip-mcp>" } } }` |
| **Hermes / mcphub** | `mcp_servers.yaml` | `- name: ctrip`<br>`  command: <abs-path-to-ctrip-mcp>` |
| **Cursor / Windsurf / Aider** | stdio 传输 | 开箱即用 |

> **坑**:`ctrip-mcp` 命令只在 `~/.ctrip-mcp/.venv/bin/` 下面,**不在
> 系统 PATH** —— 配置里必须写绝对路径,或者软链一下:
> `ln -sf ~/.ctrip-mcp/.venv/bin/ctrip-mcp /usr/local/bin/ctrip-mcp`。

## 配置参数

| 参数 / 环境变量 | 默认 | 说明 |
|---|---|---|
| `CTRIP_DATA_DIR` | `/opt/data/ctrip-data` | 7 个 GraphQL JSON + screenshot 落盘路径,需可写 |
| `CTRIP_DEPART_CITY_ID` | `2` | 上海。`ctrip_spa_capture` 入参可覆盖 |
| `CTRIP_TIMEOUT` | `60` | 单次抓取超时(秒) |
| `CTRIP_NO_SCROLL` | `false` | `1` 跳过懒加载滚动(不推荐,丢后半段) |
| `REDNOTE_COOKIES` | _(未设)_ | xhs 工具的 cookie 字符串,格式 `a1=xxx; web_session=yyy; …` |
| `REDNOTE_COOKIES_FILE` | _(未设)_ | 备选:cookie 文件路径。`REDNOTE_COOKIES` 优先 |

## 仓库结构

```
ctrip-mcp/
├── AGENTS.md                          # Claude Code / Hermes / Codex / Aider 自动读
├── bootstrap.sh                       # 一行安装
├── mcp_register.sh                    # 自动注册 ctrip 到 Claude/Cursor/Windsurf/mcphub
├── install-as-skill.sh                # 把 skill 软链进 ~/.hermes/skills/
├── pyproject.toml
├── src/
│   ├── ctrip_mcp/
│   │   ├── server.py                  # 5 个 MCP 工具 (stdio)
│   │   └── capture.py                 # Playwright + fetch hook
│   └── rednote_mcp/                   # 打包的小红书姊妹工具 (4 个)
├── scripts/
│   ├── test_e2e.py
│   └── install_deps.sh                # apt 装 chromium 系统库
└── skill/                             # 4 个 agent skill
    ├── ctrip-product-research/        # umbrella
    ├── ctrip-spa-capture/
    ├── ctrip-product-report/
    └── ctrip-product-decision-deck/   # v5 PPT
```

## 开源协议

[MIT](LICENSE)
