#!/usr/bin/env bash
# install-as-skill.sh — 把本仓库注册为 Hermes Agent 的 skill
#
# 用法 (在 ctrip-mcp 仓库根目录):
#   bash install-as-skill.sh
#
# 行为:
#   - 软链 skill/ → ~/.hermes/skills/ctrip-<subname>
#   - 软链 pyproject.toml 配置的 bin entry → ~/.hermes/bin/ctrip-mcp
#   - 提示用户加 .mcp.json / config.yaml

set -e

REPO=$(cd "$(dirname "$0")" && pwd)
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
SKILLS_DIR="$HERMES_HOME/skills"
BIN_DIR="$HERMES_HOME/bin"

echo "▶ ctrip-mcp skill 安装"
echo "  仓库: $REPO"
echo "  Hermes: $HERMES_HOME"

mkdir -p "$SKILLS_DIR" "$BIN_DIR"

# skill 软链 (3 个)
for sub in ctrip-product-research ctrip-spa-capture ctrip-product-report; do
  src="$REPO/skill/$sub"
  dst="$SKILLS_DIR/$sub"
  if [ -d "$src" ]; then
    rm -rf "$dst"
    ln -s "$src" "$dst"
    echo "  ✓ $dst → $src"
  fi
done

# bin 软链 (如果 venv 已存在)
VENV="$REPO/.venv"
if [ -x "$VENV/bin/ctrip-mcp" ]; then
  ln -sf "$VENV/bin/ctrip-mcp" "$BIN_DIR/ctrip-mcp"
  echo "  ✓ $BIN_DIR/ctrip-mcp"
fi

# .mcp.json 提示
if [ ! -f "$REPO/.mcp.json" ] && [ -f "$REPO/.mcp.json.example" ]; then
  cp "$REPO/.mcp.json.example" "$REPO/.mcp.json"
  echo "  ✓ 创建 $REPO/.mcp.json (Claude Code 自动识别)"
fi

cat <<EOF

✓ 安装完成

下一步:
  [Claude Code]  cd $REPO && claude  # 自动读 .mcp.json
  [Hermes]        restart Hermes  # 自动读 ~/.hermes/skills/
  [直接验证]      python $REPO/scripts/test_e2e.py

EOF
