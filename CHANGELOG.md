# 更新日志 (CHANGELOG)

## [0.5.0] - 2026-06-07

### docs — README rewrite (PinchBench style) + mcp_register.sh + 双语同步

#### README 公开化重写 (commit 4961f10)
- PinchBench 范式: ASCII hero (pyfiglet smslant 5 行) + 3 徽章 + 单行副标题 + 左对齐标题
- 工具数 5 → 9 (5 ctrip_* + 4 xhs_*), 跟 server.py 真实工具名对齐
- 新建 README.zh-CN.md (~7.8KB), 与 README.md 严格对称

#### mcp_register.sh — 客户端零手动配置 (commit f97a182)
- 新加 8.4KB / +x 脚本: 探测 $CTRIP_MCP_BIN env → which → ~/.ctrip-mcp/.venv/bin/ → /usr/local/bin
- 自动注册 ctrip entry 到 4 客户端: Claude Code / Cursor / Windsurf / Hermes-mcphub
- 用 venv 自带 python3 (避免系统 python 缺 yaml) 写 JSON/YAML
- 保留其它 mcpServers entry, 不覆盖; 支持 --dry-run / --unregister 幂等
- bootstrap.sh #9 节自动调脚本, 末尾 #10 节保留手动 fallback 提示

#### Client wiring 节扩展 (commit 221dcdb)
- Symlink shortcut: `ln -sf ~/.ctrip-mcp/.venv/bin/ctrip-mcp /usr/local/bin/ctrip-mcp`
  → 之后配置可原样用 "command": "ctrip-mcp"
- Rednote (XHS) cookies 完整节: 9 工具真实名 + cookie 注入优先级 + 抓取 30s 教程
- **REDNOTE_COOKIES_FILE 提示框**: 控制 xhs_* 是否在 tools/list 显示, REDNOTE_COOKIES
  env 配了能跑工具但 MCP 客户端看不见, **必须配 REDNOTE_COOKIES_FILE**

#### 元数据 + 隐私
- bootstrap.sh 仓库 URL 全切 github (commit 7542a3b): gitee.com → github.com
- .gitignore 加 browser_data/ (commit f98aad7): Chrome Cookies SQLite 含 6 个 xhs cookie
- browser_data/ 移出仓库归档到 /opt/data/ctrip-mcp-browser_data-archive.20260607-225708/
- **版本号全栈对齐 0.1.0 → 0.5.0**: pyproject.toml + src/ctrip_mcp/__init__.py 双写
- **serverInfo 修复**: server.py:45 `app = Server("ctrip-mcp")` → `app = Server("ctrip-mcp", version=__version__)`
  之前 serverInfo.version 错误地报 MCP SDK 版本 (1.27.2), 修后正确报 ctrip-mcp 0.5.0
  stdio 启动验证: ✅ server reports name='ctrip-mcp' version='0.5.0'

#### 公开发布
- 推到 GitHub: https://github.com/weber-pan/ctrip-mcp (HTTPS+PAT, SSH 22 被墙)
- 同步 Gitee: git@gitee.com:weber-pan/ctrip-mcp.git (SSH, 本机 key 已认证)

## [0.3.0] - 2026-06-07

### 升级 — ctrip-product-decision-deck v5 (旅客决策手册 + 官方图)

#### 4 沙巴 1 印尼 双案例落地
- **p69852382 巴厘岛 7 日 5 晚** (v3 含图版, 1.22 MB / 28 页)
  - A 高性价5钻 ¥5,836 起 / B 小众秘境 ¥7,409 / C 2晚阿雅娜 ¥10,348 / D 全国联运 ¥5,254
  - 13 张官方图嵌入 (10 POI + 3 酒店实拍, JSON 4 类字段源)
  - P26-P28 三张图集页 (4 线代表图 / 酒店精选 / 行程 9 景点 3x3 网格)
- **p64158367 沙巴 6 日 5 晚** (4 线对比 28 页) — 7/4-7/10 价格矩阵完整

#### SKILL.md v5 增量 (10.7 节 v3 必抓 SOP)
- **4 类必抓图 JSON 路径**: `imageStyleInfo.poiInfo.ImagePoiList[]` / `hotelInfo.imageHotelList[].imageList[]` / `commentInfo.comments[].userInfo.avatarUrl` / `productExtend.MoreRecommendProductList[].ImageUrl`
- **PIL 缩图规范**: 800x600 / q82 / optimize / RGBA → RGB
- **3 张图集页规范**: P26 4 线代表图 + P27 酒店精选 + P28 行程 9 景点网格
- **v3 pptx 验证**: ZIPFILE 检查 `ppt/media/image_*.jpg` 嵌入数
- **附 6 个新 reference**: case-p69852382 / lessons-failures-bank / multi-line-4-bundle-compare / pitfalls-overview / quality-bar / v5-increment-update

#### 教训固化 (3 轮迭代 v1→v2→v3)
- v1 缺 4 线 → v2 补 → v3 缺图 → **3 张图集页 + 13 张官方图嵌入** → 永久 skill 化
- 用户原话: "基本对比+官方的图片 也没插入到 ppt 里面啊 你都没写进 skill 里面吗"

### 与 ppt-master 守则联动
- **ppt-master SKILL.md** 也追加「产品类 PPT 必走 7 项检查」(2026-06-07 p69852382 教训) — 3 路硬链同步
- 任何产品 PPT 必须含 4 线对比表 + ≥3 张图集页 + 4 类必抓图

## [0.2.0] - 2026-06-06

### 新增 — 0 跑体验
- **bootstrap.sh** (3.8KB) — 任意环境一条命令安装
  - `curl -fsSL https://gitee.com/weber-pan/ctrip-mcp/raw/master/bootstrap.sh | bash`
  - 自动: 探测 Python ≥ 3.10 / git clone / venv / pip install / chromium / e2e 测试
- **install-as-skill.sh** (1.5KB) — 注册 3 个 skill 软链到 `~/.hermes/skills/`
- **AGENTS.md** (4KB) — Claude Code / Hermes / Codex / Aider 自动读
  - 5 工具表 + 7 个 pitfall + city 字典
- **.mcp.json.example** — Claude Code 一键接入
- **docs/HERMES_CONFIG.yaml.example** — Hermes config 片段
- README 重写 (11.4KB, 12 节)
  - 0 跑引导 / 3 层架构图 / city 字典 / 8 坑日志 / 5 客户端接入

### 升级 — 数据维度
- 印尼 p69762187 验证 11 段补漏:
  - 价格日历 207 天 (CSV 落盘)
  - 行程 10 段 SegmentInfo (不靠 DOM)
  - 9 家酒店 + 8 POI (带 hotelId/poiId, 可调 hotelMCP)
  - 68 城价 / 销量 328 / 流量 8636
  - 15+ 张图片 (4 类源)
  - 8 个竞品比价 / 11 段报告模板

### 升级 — Skill 系统
- `skill/ctrip-spa-capture/` (3 SKILL.md + 3 脚本 + 4 reference, 84KB)
- `skill/ctrip-product-report/` (1 SKILL.md + 1 脚本 + 8 reference, 92KB)
- `skill/ctrip-product-research/` (umbrella, 8KB)

### 测试
- 沙巴 p64158367: 4 线路 / 7/4 ¥6857-¥8365
- 印尼 p69762187: 1 线路 / 9 酒店 / 8 POI / 207 天价 / 11 段
- 印尼 p42461732: 1 线路 / 5 酒店 / 9 POI / 352 天价

## [0.1.0] - 2026-06-06

### 新增
- 首版发布
- 5 个 MCP 工具:
  - `ctrip_spa_capture` — 抓 m 端 h5 SPA 真实 graphql/soa body
  - `ctrip_get_product` — 解析产品 (4 条线/价格/酒店/点评)
  - `ctrip_compare_subproducts` — 4 条线逐线对比
  - `ctrip_get_hotel_price` — 酒店真实房价 (走 AI_Go_Hotel_MCP)
  - `ctrip_health` — 健康检查
- 零 token 设计 (抓的是公开接口, 无鉴权)
- Playwright + chromium 抓取核心 (`capture.py`)
- 完整真实数据: 4 条线路 / 8 家酒店 / 7 月全月价格 / 点评 / 合同方
- 5 个 pitfalls 文档化

### 已知限制
- Playwright 抓取 ~25s/产品 (浏览器启动 + SPA lazy load)
- 容器需预装 chromium (~150MB, `uv run playwright install chromium`)
- sub-product graphql 字段不全, B/C/D 行程要从 DOM 文本 `D\d\|📍` 正则抽
- 4 条线点评数据相同 (新产品模板, 等真实用户分线评价)
- 8 家 5 钻酒店里 MCP 只命中 3 家 (凯悦尚萃/丹绒亚路/艾美), 其余 5 家走 wendao 兜底

### 与姊妹项目 wendao 版的关系
- 本仓库 (ctrip-mcp): 真抓 (无 token, 25s/产品)
- 姊妹仓库 (xiecheng-mcp): wendao LLM 兜底 (需 token, 10-30s/query)
- 建议两个都装, 优先用本仓库, wendao 兜底

## [0.4.0] - 2026-06-07

### feat — 内嵌 rednote-mcp (小红书真实数据, 条件集成)

#### 4 个 xhs_* tool (有 cookie 才暴露, 无 cookie 隐藏)
- 启动时检测 `REDNOTE_COOKIES_FILE` → 有 cookie 才注册 xhs_* tool
- 无 cookie → ctrip-mcp 只暴露 5 个 ctrip_* tool, xhs_* 完全不可见
- mcphub 配 env: `REDNOTE_COOKIES_FILE=/app/.secrets/xhs_cookies.json`

#### 集成实现
- 复用 rednote-mcp 浏览器实例 + cookie (一份 cookie 两个模块共享)
- 已验证端到端: 京都7日游 / 日本7日游 搜到 5+ 条真笔记
- ctrip_health 自动展示 xhs 子模块状态 (cookie 文件/登录态/浏览器)

#### 触发场景
- "站旅客角度"/"真实攻略"/"小红书数据" → xhs_search_notes
- "用户游记"/"价格实测"/"避坑" → xhs_get_note_content
- 数据源: https://github.com/JonaFly/RednoteMCP (基于此改编)
