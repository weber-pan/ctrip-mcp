# 更新日志 (CHANGELOG)

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
