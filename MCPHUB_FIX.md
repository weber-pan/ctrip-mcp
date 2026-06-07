# MCPHUB 配置修复 (2026-06-07)

## 问题
mcphub 编辑界面配的 `Command` 是 `/root/.ctrip-mcp/.venv/bin/python`,
但容器是 hermes 用户, `/root` 不可写, 该路径不存在.
mcphub 拿到配置 → spawn 子进程 → 找不到 python → **Connection closed** (MCP error -32000).

## 修复 (3 个字段改 mcphub)

```
Command:    /opt/data/.venv/bin/python
Arguments:  -m ctrip_mcp.server
cwd:        /opt/data/ctrip-mcp
Environment Variables:
  CTRIP_DATA_DIR              /opt/data/ctrip-data
  PLAYWRIGHT_BROWSERS_PATH    /opt/data/home/.cache/ms-playwright
```

⚠ **不要** 用 `${CTRIP_PYTHON:-/opt/hermes/.venv/bin/python}` 这种 envsubst 语法,
mcphub 不展开, 直接当字面量传给 spawn.

## 同时修了 server.py 的 bug

`src/ctrip_mcp/server.py` 用了 mcp SDK 1.27 之前的 `stdio_server(app)` 签名,
新版 SDK 是 `stdio_server()` (无参). 已修.

## 已验证

```bash
cd /opt/data/ctrip-mcp
echo '{"jsonrpc":"2.0","id":1,"method":"initialize",...}
{"jsonrpc":"2.0","method":"notifications/initialized"}
{"jsonrpc":"2.0","id":2,"method":"tools/list"}' | /opt/data/.venv/bin/python -m ctrip_mcp.server
```

返回 5 tools: `ctrip_spa_capture` / `ctrip_get_product` /
`ctrip_compare_subproducts` / `ctrip_get_hotel_price` / `ctrip_health` ✅

## 安装 (在 hermes 容器内)

```bash
/opt/data/.venv/bin/python -m pip install -e /opt/data/ctrip-mcp
```

`pip` 已装好 + `ctrip_mcp` 0.1.0 editable install OK.
chromium 已在 `/opt/data/home/.cache/ms-playwright/chromium-1223/`.
