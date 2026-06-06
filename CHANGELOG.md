# 更新日志 (CHANGELOG)

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
- 2 个 reference 文档:
  - `ctrip-spa-graphql-hook.md` — graphql hook 技术细节
  - `hotels_mcp_ids.md` — 8 家酒店 MCP ID 对照
- 1 个 docs 文档:
  - `MCPHUB_INTEGRATION.md` — mcphub 接入指南

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
