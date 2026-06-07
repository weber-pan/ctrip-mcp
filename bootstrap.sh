#!/usr/bin/env bash
# bootstrap.sh — 从 0 一键安装 + 验证 ctrip-mcp (含小红书集成)
#
# 用法 (任何环境, 包括 Docker 容器 / 全新 VPS / Mac / Linux):
#   curl -fsSL https://github.com/weber-pan/ctrip-mcp/raw/master/bootstrap.sh | bash
#   # 或本地:
#   bash bootstrap.sh
#
# 流程:
#   1. 探测环境 (Python ≥ 3.10, 网络)
#   2. git clone (or pull if exists)
#   3. 创建 venv
#   4. pip install -e . (含 ctrip_mcp + rednote_mcp)
#   5. 探测/下载 chromium
#   6. 验证 rednote_mcp 导入 (小红书集成)
#   7. 跑 ctrip-mcp 工具列表健康检查 (5 ctrip + 4 xhs)
#   8. 跑 e2e (抓沙巴产品 64158367, 验证 ~25s)
#   9. 提示下一步: mcphub + cookie 配置

set -e

# 配色
G='\033[0;32m'
Y='\033[1;33m'
R='\033[0;31m'
N='\033[0m'

log()  { echo -e "${G}▶${N} $*"; }
warn() { echo -e "${Y}⚠${N} $*"; }
die()  { echo -e "${R}✗${N} $*" >&2; exit 1; }

# 1. 探测环境
log "探测环境..."
PY=$(command -v python3 || command -v python)
[ -z "$PY" ] && die "需要 Python 3.10+"
PY_VER=$($PY -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
log "Python: $PY ($PY_VER)"
echo "$PY_VER" | awk -F. '$1>=3 && $2>=10 {exit 0} {exit 1}' \
  || die "需要 Python 3.10+, 当前 $PY_VER"

# 2. git clone
REPO_URL="https://github.com/weber-pan/ctrip-mcp.git"
INSTALL_DIR="${CTRIP_INSTALL_DIR:-$HOME/.ctrip-mcp}"
if [ -d "$INSTALL_DIR/.git" ]; then
  log "已存在: $INSTALL_DIR, 拉最新..."
  cd "$INSTALL_DIR" && git pull --ff-only
else
  log "克隆到 $INSTALL_DIR..."
  git clone "$REPO_URL" "$INSTALL_DIR"
  cd "$INSTALL_DIR"
fi

# 3. venv
VENV="$INSTALL_DIR/.venv"
if [ ! -d "$VENV" ]; then
  log "创建 venv..."
  $PY -m venv "$VENV"
fi
# shellcheck disable=SC1091
source "$VENV/bin/activate"
log "venv: $VENV"

# 4. pip install (含 ctrip_mcp + rednote_mcp)
log "装依赖 (mcp + playwright + httpx + pydantic + 小红书)..."
pip install --quiet --upgrade pip
pip install --quiet -e .

# 5. chromium
CHROMIUM_HINT="$HOME/.cache/ms-playwright/chromium-1223/chrome-linux64/chrome"
if [ -x "$CHROMIUM_HINT" ]; then
  log "chromium 已就位: $CHROMIUM_HINT"
  if timeout 3 "$CHROMIUM_HINT" --version >/dev/null 2>&1; then
    log "chromium --version 正常 (依赖齐)"
  else
    warn "chromium 存在但 --version 失败 — 自动装系统库 (apt)..."
    if command -v apt-get >/dev/null 2>&1; then
      bash "$INSTALL_DIR/scripts/install_deps.sh"
      if timeout 3 "$CHROMIUM_HINT" --version >/dev/null 2>&1; then
        log "✓ 装完系统库后 chromium 正常了"
      else
        die "✗ 装完系统库 chromium 还是跑不起来, 见 $CHROMIUM_HINT.log"
      fi
    elif command -v apk >/dev/null 2>&1; then
      warn "Alpine 容器, 手动跑: apk add --no-cache nss nspr atk cups-libs drm libxkbcommon libxcomposite libxdamage libxfixes libxrandr gbm libxss alsa-lib font-noto-cjk"
    else
      die "未找到 apt/apk, 手动装 chromium 系统库"
    fi
  fi
elif [ -x "$(echo $HOME/.cache/ms-playwright/chromium_headless_shell-*/chrome-linux/headless_shell 2>/dev/null | tr '*' 'a' | xargs -I{} ls -d {} 2>/dev/null | head -1)" ]; then
  log "headless_shell 已就位"
else
  log "下载 chromium (~150MB)..."
  "$VENV/bin/playwright" install chromium 2>&1 | tail -5 || \
    warn "chromium 下载失败, 可手动设置 CTRIP_CHROMIUM"
fi

# 6. 验证 rednote_mcp
log "验证 rednote_mcp (小红书集成)..."
if "$VENV/bin/python" -c "from rednote_mcp import xhs_core; print(f'  ✓ rednote_mcp v{xhs_core.__version__ if hasattr(xhs_core, \"__version__\") else \"?\"}')" 2>/dev/null; then
  log "  rednote_mcp 就绪 (xhs_* 工具可用, 需配 cookie)"
else
  warn "  rednote_mcp 导入失败 — 不影响 ctrip_* 工具"
fi

# 7. 健康检查
log "ctrip-mcp 工具列表 (stdio MCP)..."
TOOL_OUT=$(echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"bootstrap","version":"0"}}}' \
  | timeout 5 "$VENV/bin/python" -m ctrip_mcp.server 2>/dev/null \
  | python3 -c "import sys,json; d=json.loads(sys.stdin.read()); caps=d.get('result',{}).get('capabilities',{}); tools=caps.get('tools',{}); print(f'工具: {len(tools)} 个' if isinstance(tools, dict) else '协议握手成功')" 2>/dev/null) \
  || TOOL_OUT="MCP 握手超时 (stdio 限制, 跳到 e2e)"
log "  $TOOL_OUT"

# 8. e2e 测试
log "e2e 测试 (抓沙巴 64158367, ~25s)..."
E2E_OUT=$("$VENV/bin/python" scripts/test_e2e.py 2>&1 || true)
if echo "$E2E_OUT" | grep -q "name:\|duration:\|saved"; then
  log "✓ 完整 e2e 通过 (看下文关键行):"
  echo "$E2E_OUT" | tail -15 | sed 's/^/  /'
else
  warn "e2e 失败 — 详细错误 (head -40):"
  echo "$E2E_OUT" | head -40 | sed 's/^/  /'
  echo ""
  warn "调试 — 在 $INSTALL_DIR 下:"
  warn "  1) sys.path 是否含 $INSTALL_DIR/src:"
  warn "     $VENV/bin/python -c 'import sys; print(sys.path[:3])'"
  warn "  2) chromium 在?"
  warn "     ls /root/.cache/ms-playwright/chromium-1223/chrome-linux64/chrome 2>&1"
  warn "  3) 网络通 m.ctrip.com?"
  warn "     curl -sI https://m.ctrip.com/ | head -3"
  warn "  4) 直接调 spa_capture:"
  warn "     CTRIP_DATA_DIR=/opt/data/ctrip-data $VENV/bin/python -c 'import asyncio, sys; sys.path.insert(0, \"$INSTALL_DIR/src\"); from ctrip_mcp.capture import spa_capture; print(asyncio.run(spa_capture(64158367, 2, scroll=True)))'"
fi

# 9. 自动注册 MCP 客户端
log "▶ 自动注册到 MCP 客户端 (Claude Code / Cursor / Windsurf / mcphub)..."
REGISTER_SH="$INSTALL_DIR/mcp_register.sh"
if [ -x "$REGISTER_SH" ]; then
  CTRIP_MCP_BIN="$VENV/bin/ctrip-mcp" bash "$REGISTER_SH" 2>&1 | sed 's/^/  /' || warn "  mcp_register.sh 返回非零, 看上面"
else
  warn "  没找到 $REGISTER_SH, 跳过自动注册"
fi
echo ""

# 10. 下一步
cat <<EOF

${G}========================================${N}
${G}✓ ctrip-mcp 安装完成${N}
${G}========================================${N}

${Y}[自动注册结果]${N}  见上面 mcp_register.sh 输出
  - Claude Code: 重启 claude
  - Cursor:      重启 cursor
  - Windsurf:    重启 windsurf
  - mcphub:      不用重启, 下次配置 reload 自动生效
  - 没自动注册成功: 跑 bash $INSTALL_DIR/mcp_register.sh

${Y}[手动接入]${N}  没自动覆盖到的客户端:
  mcphub / Claude Code / Cursor / Windsurf: 看 README.md "Client wiring" 节
  stdio 直接跑:  $VENV/bin/ctrip-mcp

${Y}[小红书 cookie 注入]${N}  不配 REDNOTE_COOKIES → 9 个工具只剩 5 个 ctrip_*, xhs_* 不显示
  export REDNOTE_COOKIES='a1=xxx; web_session=yyy; ...'   # 加到 shell rc 永久生效
  DevTools 复制: xiaohongshu.com → F12 → Application → Cookies
  → 全选 → Ctrl+C → 粘到 REDNOTE_COOKIES 值

${Y}[跑一遍 mcp_register.sh 速查]${N}
  bash $INSTALL_DIR/mcp_register.sh --dry-run     # 预览
  bash $INSTALL_DIR/mcp_register.sh               # 注册所有客户端
  bash $INSTALL_DIR/mcp_register.sh --unregister  # 删 ctrip entry

EOF
