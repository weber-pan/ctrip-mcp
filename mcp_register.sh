#!/usr/bin/env bash
# mcp_register.sh — 注册 ctrip-mcp 到常见 MCP 客户端 (幂等, 可重跑)
#
# 探测顺序找 ctrip-mcp 可执行:
#   1) $CTRIP_MCP_BIN 环境变量
#   2) which ctrip-mcp
#   3) $INSTALL_DIR/.venv/bin/ctrip-mcp
#   4) ~/.ctrip-mcp/.venv/bin/ctrip-mcp
#   5) /usr/local/bin/ctrip-mcp
#
# 注册目标 (检测到哪个目录就写哪个):
#   - Claude Code:    ~/.claude/mcp.json
#   - Cursor:         ~/.cursor/mcp.json
#   - Windsurf:       ~/.codeium/windsurf/mcp_config.json
#   - Hermes/mcphub:  ~/.config/mcphub/mcp_servers.yaml
#
# 用法:
#   bash mcp_register.sh               # 自动注册到所有检测到的客户端
#   bash mcp_register.sh --dry-run     # 只打印, 不写
#   bash mcp_register.sh --unregister  # 删除已有 ctrip entry
#   CTRIP_MCP_BIN=/abs/path bash mcp_register.sh
#
# 退出码:
#   0 = 至少一个客户端配置成功
#   1 = 找不到 ctrip-mcp 可执行
#   2 = 没有可注册的客户端 (都没装)

set -uo pipefail

# ---- 配色 (跟 bootstrap.sh 一致) ----
G='\033[0;32m'; Y='\033[1;33m'; R='\033[0;31m'; C='\033[0;36m'; N='\033[0m'
log()  { echo -e "${G}▶${N} $*"; }
warn() { echo -e "${Y}⚠${N}  $*"; }
die()  { echo -e "${R}✗${N}  $*" >&2; exit 1; }
ok()   { echo -e "${G}✅${N} $*"; }
section() { echo -e "\n${C}─── $* ───${N}"; }

DRY_RUN=0
UNREGISTER=0
for arg in "$@"; do
  case "$arg" in
    --dry-run)    DRY_RUN=1 ;;
    --unregister) UNREGISTER=1 ;;
    -h|--help)
      grep -E '^#( |$)' "$0" | sed 's/^# \?//'
      exit 0
      ;;
  esac
done

# ---- 0. 找 venv 自带的 python3 (避免系统 python3 缺 yaml / chromadb / ...) ----
find_python() {
  local venv_py
  # 优先级: 跟 ctrip-mcp 同 venv 的 python3
  venv_py="$(dirname "$CTRIP_MCP_BIN")/python3"
  if [ -x "$venv_py" ]; then echo "$venv_py"; return 0; fi
  # fallback: 系统 python3
  command -v python3 || echo "python3"
}
PYTHON3="$(find_python)"
# 此时 CTRIP_MCP_BIN 还没找到, 延迟到 section 1 之后再覆盖
PYTHON3="${PYTHON3:-$(command -v python3 || echo python3)}"

# ---- 1. 探测 ctrip-mcp 真实路径 ----
section "1) 探测 ctrip-mcp 可执行位置"

CTRIP_MCP_BIN="${CTRIP_MCP_BIN:-}"
if [ -n "$CTRIP_MCP_BIN" ] && [ -x "$CTRIP_MCP_BIN" ]; then
  : # 显式指定, 跳过探测
elif command -v ctrip-mcp >/dev/null 2>&1; then
  CTRIP_MCP_BIN="$(command -v ctrip-mcp)"
else
  for cand in \
    "${INSTALL_DIR:-}/.venv/bin/ctrip-mcp" \
    "$HOME/.ctrip-mcp/.venv/bin/ctrip-mcp" \
    "/opt/data/ctrip-mcp/.venv/bin/ctrip-mcp" \
    "/usr/local/bin/ctrip-mcp"
  do
    if [ -x "$cand" ]; then CTRIP_MCP_BIN="$cand"; break; fi
  done
fi

if [ -z "$CTRIP_MCP_BIN" ] || [ ! -x "$CTRIP_MCP_BIN" ]; then
  die "找不到 ctrip-mcp 可执行。
  先跑:
    curl -fsSL https://github.com/weber-pan/ctrip-mcp/raw/master/bootstrap.sh | bash
  装好之后再跑:
    bash mcp_register.sh
  或显式指定:
    CTRIP_MCP_BIN=/path/to/ctrip-mcp bash mcp_register.sh"
fi
ok "ctrip-mcp: $CTRIP_MCP_BIN"

# 现在能确定 venv python3 了
PYTHON3="$(find_python)"
log "  python3: $PYTHON3 ($( "$PYTHON3" -c 'import sys;print(sys.executable)' 2>/dev/null || echo '?'))"

# 健康检查
if ! "$CTRIP_MCP_BIN" --help 2>&1 | head -3 | grep -qiE 'ctrip|mcp'; then
  warn "ctrip-mcp --help 输出异常, 但继续 (server 可能要 stdio 启动)"
fi

# ---- 2. 探客户端目录 ----
section "2) 探 MCP 客户端"

CLAUDE_DIR="$HOME/.claude"
CURSOR_DIR="$HOME/.cursor"
WINDSURF_DIR="$HOME/.codeium/windsurf"
HERMES_DIR="$HOME/.config/mcphub"

declare -A CLIENTS=(
  ["Claude Code"]="$CLAUDE_DIR"
  ["Cursor"]="$CURSOR_DIR"
  ["Windsurf"]="$WINDSURF_DIR"
  ["Hermes/mcphub"]="$HERMES_DIR"
)

# 探到哪个目录就注册哪个 (有目录 或 父目录可写)
declare -A TARGETS=()
for name in "${!CLIENTS[@]}"; do
  dir="${CLIENTS[$name]}"
  if [ -d "$dir" ] || [ -d "$(dirname "$dir")" ]; then
    TARGETS[$name]="$dir"
    log "  检测到: $name ($dir)"
  else
    log "  未安装: $name ($dir 不存在, 跳过)"
  fi
done

if [ "${#TARGETS[@]}" -eq 0 ]; then
  warn "没探到任何 MCP 客户端目录 (Claude/Cursor/Windsurf/Hermes 都没装)"
  warn "装好任一客户端后重跑: bash mcp_register.sh"
  exit 2
fi

# ---- 3. 写配置 ----
section "3) 写 MCP 配置"

# Python 一行: 幂等加 ctrip entry, 保留其它 server
WRITE_MCP_JSON='
import json, sys, os
path = sys.argv[1]
cmd  = sys.argv[2]
key  = "mcpServers"
data = {}
if os.path.exists(path):
    try:
        with open(path) as f:
            txt = f.read().strip()
            if txt:
                data = json.loads(txt)
    except Exception as e:
        print(f"WARN: 解析 {path} 失败: {e}; 按空配置覆盖", file=sys.stderr)
        data = {}
if key not in data or not isinstance(data[key], dict):
    data[key] = {}
data[key]["ctrip"] = {
    "command": cmd,
    "env": {
        "CTRIP_DATA_DIR": "/opt/data/ctrip-data"
    }
}
os.makedirs(os.path.dirname(path), exist_ok=True)
with open(path, "w") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
    f.write("\n")
print(f"  写入: {path}")
'

# Python 一行: 幂等删 ctrip entry
DELETE_MCP_JSON='
import json, sys, os
path = sys.argv[1]
key  = "mcpServers"
if not os.path.exists(path):
    print(f"  跳过 (不存在): {path}")
    sys.exit(0)
try:
    with open(path) as f:
        data = json.load(f)
except Exception as e:
    print(f"  解析失败: {e}", file=sys.stderr)
    sys.exit(1)
if key in data and isinstance(data[key], dict) and "ctrip" in data[key]:
    del data[key]["ctrip"]
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"  删除 ctrip: {path}")
else:
    print(f"  无 ctrip entry: {path}")
'

# Python 一行: 写 mcphub YAML
WRITE_MCP_YAML='
import sys, os
try:
    import yaml
except ImportError:
    print("  PyYAML 缺, 跳过 (pip install pyyaml 后重试)", file=sys.stderr)
    sys.exit(2)
path = sys.argv[1]
cmd  = sys.argv[2]
data = []
if os.path.exists(path):
    with open(path) as f:
        data = yaml.safe_load(f) or []
        if not isinstance(data, list):
            data = []
data = [d for d in data if not (isinstance(d, dict) and d.get("name") == "ctrip")]
data.append({
    "name": "ctrip",
    "command": cmd,
    "env": {"CTRIP_DATA_DIR": "/opt/data/ctrip-data"},
})
os.makedirs(os.path.dirname(path), exist_ok=True)
with open(path, "w") as f:
    yaml.safe_dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
print(f"  写入: {path}")
'

# Python 一行: 删 mcphub YAML
DELETE_MCP_YAML='
import sys, os
try:
    import yaml
except ImportError:
    sys.exit(0)
path = sys.argv[1]
if not os.path.exists(path):
    print(f"  跳过 (不存在): {path}")
    sys.exit(0)
with open(path) as f:
    data = yaml.safe_load(f) or []
data = [d for d in data if not (isinstance(d, dict) and d.get("name") == "ctrip")]
with open(path, "w") as f:
    yaml.safe_dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
print(f"  删除 ctrip: {path}")
'

ANY_SUCCESS=0

# 处理 JSON 客户端: Claude Code / Cursor / Windsurf
write_json() {
  local name="$1" dir="$2" file="$3"
  if [ -z "$dir" ]; then return 0; fi
  local cfg="$dir/$file"
  if [ "$UNREGISTER" = "1" ]; then
    if [ "$DRY_RUN" = "1" ]; then echo "[DRY] python3 -c ... $cfg"; return 0; fi
    "$PYTHON3" -c "$DELETE_MCP_JSON" "$cfg" 2>&1 && ANY_SUCCESS=1 || warn "  失败: $cfg"
  else
    if [ "$DRY_RUN" = "1" ]; then echo "[DRY] 写入 ctrip entry: $cfg (command=$CTRIP_MCP_BIN)"; return 0; fi
    "$PYTHON3" -c "$WRITE_MCP_JSON" "$cfg" "$CTRIP_MCP_BIN" 2>&1 && ANY_SUCCESS=1 || warn "  失败: $cfg"
  fi
}

write_json "Claude Code" "${TARGETS[Claude Code]:-}" "mcp.json"
write_json "Cursor"      "${TARGETS[Cursor]:-}"      "mcp.json"
write_json "Windsurf"    "${TARGETS[Windsurf]:-}"    "mcp_config.json"

# Hermes/mcphub YAML
if [ -n "${TARGETS[Hermes/mcphub]:-}" ]; then
  cfg="$HERMES_DIR/mcp_servers.yaml"
  if [ "$UNREGISTER" = "1" ]; then
    if [ "$DRY_RUN" = "1" ]; then echo "[DRY] python3 -c ... $cfg"
    elif "$PYTHON3" -c "$DELETE_MCP_YAML" "$cfg" 2>&1; then ANY_SUCCESS=1; fi
  else
    if [ "$DRY_RUN" = "1" ]; then
      echo "[DRY] 写入 ctrip entry: $cfg (command=$CTRIP_MCP_BIN)"
    elif "$PYTHON3" -c "$WRITE_MCP_YAML" "$cfg" "$CTRIP_MCP_BIN" 2>&1; then
      ANY_SUCCESS=1
    else
      warn "  失败: $cfg"
    fi
  fi
fi

# ---- 4. 总结 ----
section "完成"

if [ "$DRY_RUN" = "1" ]; then
  ok "DRY-RUN 模式, 没真写"
elif [ "$UNREGISTER" = "1" ]; then
  ok "ctrip entry 已从所有客户端配置中删除"
else
  ok "ctrip entry 已注册到 ${#TARGETS[@]} 个客户端"
  echo ""
  log "下一步:"
  echo "  - Claude Code: 重启 claude"
  echo "  - Cursor:      重启 cursor, 检查 Settings → MCP"
  echo "  - Windsurf:    重启 windsurf"
  echo "  - Hermes/mcphub: 不用重启, mcphub 改完 env 即生效"
  echo ""
  log "小红书 cookie 注入 (可选, 不配就没 xhs_* 工具):"
  echo "  export REDNOTE_COOKIES='a1=xxx; web_session=yyy; ...'"
  echo "  # 或写到 .env: REDNOTE_COOKIES=a1=xxx..."
  echo "  改完重启对应 MCP 客户端即生效"
fi

exit 0
