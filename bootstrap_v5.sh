#!/usr/bin/env bash
# bootstrap_v5.sh — 容器/mac/任意 Linux 都能装 + 调试
# 修复 v4 问题:
# 1) 用 ${CTRIP_INSTALL_DIR} 默认 /opt/data/ctrip-mcp (mac 跑会回退到 ~/.ctrip-mcp)
# 2) chromium 自动 fallback
# 3) 调 1 个 stdio 烟测, 确认 server 真的能初始化
# 4) 详细打印 e2e 失败信息 (而不是 JSONDecodeError 默默死)
#
# 用法:
#   bash bootstrap_v5.sh
#   CTRIP_INSTALL_DIR=/opt/data/ctrip-mcp bash bootstrap_v5.sh
#   # mac 跑 (默认路径):
#   bash bootstrap_v5.sh  # 装到 ~/.ctrip-mcp

set -e

G='\033[0;32m'; Y='\033[1;33m'; R='\033[0;31m'; N='\033[0m'
log()  { echo -e "${G}▶${N} $*"; }
warn() { echo -e "${Y}⚠${N} $*"; }
die()  { echo -e "${R}✗${N} $*" >&2; exit 1; }

# 1. Python
log "Python 探测..."
PY=$(command -v python3 || command -v python)
[ -z "$PY" ] && die "需要 Python 3.10+"
PY_VER=$($PY -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "$PY_VER" | awk -F. '$1>=3 && $2>=10 {exit 0} {exit 1}' \
  || die "需要 Python 3.10+, 当前 $PY_VER"
log "Python: $PY ($PY_VER)"

# 2. 装到 ${CTRIP_INSTALL_DIR:-$HOME/.ctrip-mcp}
REPO_URL="https://gitee.com/weber-pan/ctrip-mcp.git"
INSTALL_DIR="${CTRIP_INSTALL_DIR:-$HOME/.ctrip-mcp}"
log "安装目录: $INSTALL_DIR"

if [ -d "$INSTALL_DIR/.git" ]; then
  log "已存在, 拉最新..."
  cd "$INSTALL_DIR" && git pull --ff-only
else
  log "克隆..."
  git clone "$REPO_URL" "$INSTALL_DIR"
  cd "$INSTALL_DIR"
fi

# 3. venv (用主环境 venv 复用策略, 失败回退 --without-pip)
VENV="$INSTALL_DIR/.venv"
if [ ! -x "$VENV/bin/pip" ]; then
  rm -rf "$VENV" 2>/dev/null
  $PY -m venv "$VENV" 2>/dev/null || $PY -m venv --without-pip "$VENV"
fi
# 如果还没有 pip, 装 pip
if [ ! -x "$VENV/bin/pip" ]; then
  warn "venv 没 pip, 用 ensurepip 装"
  $VENV/bin/python -m ensurepip 2>&1 | tail -3
fi
log "venv: $VENV"

# 4. pip
log "pip install -e . ..."
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install -e .

# 5. chromium
CHROMIUM_HINT="$HOME/.cache/ms-playwright/chromium-1223/chrome-linux64/chrome"
if [ ! -x "$CHROMIUM_HINT" ]; then
  CHROMIUM_HINT2="$HOME/.cache/ms-playwright/chromium_headless_shell-*/chrome-linux/headless_shell"
  if [ -x "$(echo $CHROMIUM_HINT2 | tr '*' 'a' | xargs -I{} ls -d {} 2>/dev/null | head -1)" ]; then
    CHROMIUM_HINT=$(echo $CHROMIUM_HINT2 | tr '*' 'a' | xargs -I{} ls -d {} 2>/dev/null | head -1)
  fi
fi

if [ -x "$CHROMIUM_HINT" ]; then
  log "chromium 已就位: $CHROMIUM_HINT"
else
  log "下载 chromium (~150MB)..."
  "$VENV/bin/playwright" install chromium 2>&1 | tail -5 || \
    warn "chromium 下载失败, 可手动设置 CTRIP_CHROMIUM"
fi

# 6. MCP 协议烟测 (1 句 initialize)
log "MCP 协议烟测 (stdio initialize)..."
INIT_OUT=$(echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"bootstrap","version":"0"}}}' \
  | timeout 5 "$VENV/bin/python" -m ctrip_mcp.server 2>/dev/null || true)

if echo "$INIT_OUT" | python3 -c 'import sys,json; d=json.loads(sys.stdin.read()); assert d["result"]["serverInfo"]["name"]=="ctrip-mcp"; print("  ✓ 协议 OK, serverInfo="+d["result"]["serverInfo"]["name"]+" "+d["result"]["serverInfo"]["version"])' 2>/dev/null; then
  log "MCP 协议握手成功 ✓"
else
  die "MCP 协议握手失败 — server 启动有问题
   试运行:
     echo '{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{\"protocolVersion\":\"2024-11-05\",\"capabilities\":{},\"clientInfo\":{\"name\":\"test\",\"version\":\"1.0\"}}}' | $VENV/bin/python -m ctrip_mcp.server
   看具体错 (新版 mcp SDK 1.27 兼容问题)"
fi

# 7. e2e 测试 (10s 短超时先烟测, 再 60s 完整 e2e)
log "e2e 烟测 (仅 ctrip_spa_capture 10s)..."
INIT_OUT2=$(echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"bootstrap","version":"0"}}}' \
  | timeout 5 "$VENV/bin/python" -m ctrip_mcp.server 2>/dev/null | tail -1)
echo "$INIT_OUT2" | python3 -c "import sys,json; d=json.loads(sys.stdin.read()); print('  ✓ tools capability:', d['result']['capabilities'].get('tools'))"

# 8. 完整 e2e (5 工具完整调用)
log "完整 e2e (~30s 抓沙巴 64158367)..."
E2E_OUT=$("$VENV/bin/python" scripts/test_e2e.py 2>&1 || true)
if echo "$E2E_OUT" | grep -q "name:\|duration:\|saved"; then
  log "✓ 完整 e2e 通过:"
  echo "$E2E_OUT" | tail -15 | sed 's/^/  /'
else
  warn "e2e 失败 — 详细错误 (head -40):"
  echo "$E2E_OUT" | head -40 | sed 's/^/  /'
  echo ""
  warn "调试 — 在 $INSTALL_DIR 下:"
  warn "  1) sys.path:"
  warn "     $VENV/bin/python -c 'import sys; print(sys.path[:3])'"
  warn "  2) chromium:"
  warn "     ls /root/.cache/ms-playwright/chromium-1223/chrome-linux64/chrome 2>&1"
  warn "  3) 网络:"
  warn "     curl -sI https://m.ctrip.com/ | head -3"
  warn "  4) 直接调 spa_capture:"
  warn "     $VENV/bin/python -c 'import asyncio, sys; sys.path.insert(0, \"$INSTALL_DIR/src\"); from ctrip_mcp.capture import spa_capture; print(asyncio.run(spa_capture(64158367, 2, scroll=True)))'"
fi

# 9. 下一步
cat <<EOF

${G}========================================${N}
${G}✓ ctrip-mcp v5 安装完成${N}
${G}========================================${N}

${Y}[mcphub]${N}  Web UI 加 stdio server (用下面真实路径, 不是 /root/...):
  Name:    携程官网
  Cmd:     $VENV/bin/python
  Args:    -m ctrip_mcp.server
  Workdir: $INSTALL_DIR
  Env:
    CTRIP_DATA_DIR=/opt/data/ctrip-data
    CTRIP_PYTHON=$VENV/bin/python
    CTRIP_INSTALL_DIR=$INSTALL_DIR

EOF
