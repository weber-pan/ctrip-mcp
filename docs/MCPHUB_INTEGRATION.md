# ctrip-mcp 接入 mcphub (mcp.webertl.top:33399)

## 方案 A: mcphub web UI 手动加 (推荐, 1 分钟)

登录 `https://mcp.webertl.top:33399` → **MCP Servers** → **Add Server** → 选 **Stdio**:

| 字段 | 值 |
|---|---|
| Name | `ctrip` |
| Command | `uv` |
| Args | `--directory /opt/data/work/ctrip-mcp run ctrip-mcp` |
| Env (JSON) | `{}` (无需 token) |

保存 → **Test Connection** → 应该看到 5 个 tools 出现:
- `ctrip_spa_capture`
- `ctrip_get_product`
- `ctrip_compare_subproducts`
- `ctrip_get_hotel_price`
- `ctrip_health`

## 方案 B: 直接编辑 mcphub config

mcphub 配置文件通常在 Mac 端 `~/mcphub/config.yaml` 或 `~/.config/mcphub/servers.json`, 加:

```yaml
mcp_servers:
  ctrip:
    command: uv
    args:
      - --directory
      - /opt/data/work/ctrip-mcp
      - run
      - ctrip-mcp
    env: {}
    description: "携程 m 端 h5 SPA 真抓 (Playwright + chromium, 无 token)"
```

然后 mcphub 重启或点 Reload.

## 方案 C: HTTP/SSE (若有公网)

```bash
# 在 server.py 加 streamable_http transport
cd /opt/data/work/ctrip-mcp
uv run python -c "
from ctrip_mcp.server import app
import uvicorn
uvicorn.run(app, host='0.0.0.0', port=8766)
"
```

mcphub 加 `http://localhost:8766/sse` (或公网 URL).
**此方案需给 server.py 加 SSE 路由**, 目前是纯 stdio.

## 验证 (任一方案后)

```bash
# 1) 健康检查
uv --directory /opt/data/work/ctrip-mcp run ctrip-mcp
# 在 MCP 客户端里调 ctrip_health
# 应该看到 chromium 路径 + data_dir_writable: true + playwright_importable: true

# 2) 真实抓取
# 调 ctrip_spa_capture(product_id=64158367)
# 等待 ~25s, 拿到 8 个 graphql/soa 落盘路径

# 3) 解析
# 调 ctrip_get_product(product_id=64158367)
# 拿到 4 条线路 / 8 家酒店 / 7 月每日价格 / 点评
```

## 与姊妹项目 wendao 版同装

```json
{
  "mcpServers": {
    "ctrip": {
      "command": "uv",
      "args": ["--directory", "/opt/data/work/ctrip-mcp", "run", "ctrip-mcp"]
    },
    "xiecheng": {
      "command": "uv",
      "args": ["--directory", "/opt/data/work/xiecheng-mcp", "run", "xiecheng-mcp"],
      "env": {"WENDAO_API_KEY": "your_token_here"}
    }
  }
}
```

- `ctrip` = 真抓 (无 token, ~25s/产品)
- `xiecheng` = wendao 兜底 (需 token, ~10-30s/query)

## 工具列表 (装好后在 mcphub 看到)

| 工具 | 说明 | 数据源 |
|---|---|---|
| `ctrip_spa_capture` | 抓 m 端 h5 SPA 真实 graphql/soa body | Playwright + chromium |
| `ctrip_get_product` | 解析已抓取的产品数据 | 本地 JSON |
| `ctrip_compare_subproducts` | 4 条线逐线抓 (B/C/D 行程) | `ctrip_spa_capture` × N |
| `ctrip_get_hotel_price` | 查酒店真实房价 | 走 AI_Go_Hotel_MCP |
| `ctrip_health` | 健康检查 | 本地 |
