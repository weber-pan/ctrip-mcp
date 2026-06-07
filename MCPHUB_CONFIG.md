## mcphub "携程官网" 服务器正确配置

**问题根因**:
- 你的 `/root/.ctrip-mcp/.venv/bin/python` 是**root 用户路径** (mcphub 用 root 跑)
- 容器内是 `hermes` 用户,**没有 `/root/` 权限**
- 装 venv 失败 → server 起不来 → "Connection closed"

**修复方案**:改用容器内 venv 路径

---

### 字段填法(粘贴)

| 字段 | 值 |
|---|---|
| **Server Name** | 携程官网 |
| **Server Type** | STDIO |
| **Command** | `/opt/data/ctrip-mcp/.venv/bin/python` |
| **Arguments** | `-m ctrip_mcp.server` |
| **Environment Variables** | 见下(每行 1 条) |

### Environment Variables (key=value,每行 1 条)

```
CTRIP_DATA_DIR=/opt/data/ctrip-data
CTRIP_PYTHON=/opt/data/ctrip-mcp/.venv/bin/python
CTRIP_INSTALL_DIR=/opt/data/ctrip-mcp
```

### 验证步骤

1. mcphub 添加/保存 "携程官网" server
2. 等待 5-10s
3. 在 mcphub chat 输入:`ctrip_health`
4. 应返回:健康检查成功 + chromium 路径 + last capture timestamp

### 已做的修复

- ✅ 创建 venv: `/opt/data/ctrip-mcp/.venv/`
- ✅ pip install -e . 成功
- ✅ 修 server.py mcp 1.27 SDK 兼容 (stdio_server() 不接 app 参数)
- ✅ mcp initialize 协议握手 OK
- ⚠ playwright install chromium (with-deps) 需 root,失败但**已有 chromium 在 /opt/data/.venv/.cache/ms-playwright/**

### 如果还报 "Connection closed"

**最常见 3 个原因**:
1. **venv 路径错**:必须 `/opt/data/ctrip-mcp/.venv/bin/python`,**不要** `/root/...`
2. **cwd 缺**:有些 mcphub 版本要 cwd= `/opt/data/ctrip-mcp` (配置文件可能不暴露)
3. **mcp SDK 版本不兼容**:用 venv 装的 1.27(已修)

### 服务器 5 个工具

| Tool | 用途 |
|---|---|
| `ctrip_spa_capture` | Playwright 抓 SPA (≈25s) |
| `ctrip_get_product` | 解析产品 JSON |
| `ctrip_compare_subproducts` | 4 条线对比 |
| `ctrip_get_hotel_price` | 真实酒店房价 |
| `ctrip_health` | 健康检查 |

### 故障排查命令

```bash
# 1) 直接 stdin/stdout 测试
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' | /opt/data/ctrip-mcp/.venv/bin/python -m ctrip_mcp.server

# 应输出:{"jsonrpc":"2.0","id":1,"result":{"serverInfo":{"name":"ctrip-mcp","version":"0.1.0"}}}
```

```bash
# 2) venv 路径检查
ls -la /opt/data/ctrip-mcp/.venv/bin/python
# 应是 hermes 用户可执行

# 3) chromium 检查
ls -la /opt/data/.venv/.cache/ms-playwright/chromium*/chrome-linux/chrome
# 或
~/.cache/ms-playwright/chromium*/chrome-linux/chrome
```
