#!/usr/bin/env bash
# downscale_for_vision.sh
# 2026-06-07 p69762187 案例产出
#
# 用途: 把携程 SPA 抓取的 16+ 张产品图(desc banner / POI / PM / brand)
#       缩到 3 档尺寸,供 vision_analyze 或 PNG 预览使用。
#
# 触发: vision_analyze server 报 413 (size limit) 或 404 时。
#       PIL 不可用时也可走这个(PIL _imaging import 失败常见)。
#
# 用法:
#   ./downscale_for_vision.sh <product_id>           # 默认全部
#   ./downscale_for_vision.sh <product_id> desc      # 只缩 desc_*.jpg
#   ./downscale_for_vision.sh <product_id> tiny      # 强制只做 400px
#   SIZE_TINY=300 ./downscale_for_vision.sh <pid>    # 自定义尺寸
#
# 产物: /tmp/img_small/<name>_small.jpg  (800px q=5, 100-800KB)
#       /tmp/img_tiny/<name>_tiny.jpg    (400px q=15, 12-26KB)
#       /tmp/img_xs/<name>_xs.jpg        (200px q=20, <10KB)
#
# 已知坑:
#   - desc_1.jpg 3.6 MB 即使缩到 400px 仍 147 KB,可能仍触发 413 → 用 tiny
#   - 17 KB 也可能 404 → 那是 server routing 死,跟大小无关,放弃自己读

set -euo pipefail

PID="${1:-}"
FILTER="${2:-all}"

if [[ -z "$PID" ]]; then
  echo "用法: $0 <product_id> [all|desc|poi|pm|tiny]"
  exit 1
fi

SRC="/opt/data/ctrip-data/img_${PID}"
SMALL="/tmp/img_small"
TINY="/tmp/img_tiny"
XS="/tmp/img_xs"

if [[ ! -d "$SRC" ]]; then
  echo "❌ 目录不存在: $SRC (先跑 ctrip_spa_capture.py + extract_images.py)"
  exit 1
fi

mkdir -p "$SMALL" "$TINY" "$XS"

# 选文件
case "$FILTER" in
  all)  files=$(ls "$SRC"/*.jpg 2>/dev/null) ;;
  desc) files=$(ls "$SRC"/desc_*.jpg 2>/dev/null) ;;
  poi)  files=$(ls "$SRC"/poi_*.jpg 2>/dev/null) ;;
  pm)   files=$(ls "$SRC"/pm*.jpg 2>/dev/null) ;;
  tiny) files=$(ls "$SRC"/*.jpg 2>/dev/null) ;;
  *)    echo "❌ 未知 filter: $FILTER (all|desc|poi|pm|tiny)"; exit 1 ;;
esac

if [[ -z "$files" ]]; then
  echo "❌ 没找到匹配的 jpg 文件 (filter=$FILTER)"
  exit 1
fi

# 缩图三档
SIZE_SMALL="${SIZE_SMALL:-800}"
SIZE_TINY="${SIZE_TINY:-400}"
SIZE_XS="${SIZE_XS:-200}"

for f in $files; do
  base=$(basename "${f%.jpg}")
  echo "→ $base"

  # small (800px, q=5) — vision_analyze 默认档
  if [[ "$FILTER" != "tiny" ]]; then
    ffmpeg -y -i "$f" -vf "scale=${SIZE_SMALL}:-1" -q:v 5 \
      "$SMALL/${base}_small.jpg" 2>/dev/null
  fi

  # tiny (400px, q=15) — vision server 死时硬压
  ffmpeg -y -i "$f" -vf "scale=${SIZE_TINY}:-1" -q:v 15 \
    "$TINY/${base}_tiny.jpg" 2>/dev/null

  # xs (200px, q=20) — 终极兜底
  ffmpeg -y -i "$f" -vf "scale=${SIZE_XS}:-1" -q:v 20 \
    "$XS/${base}_xs.jpg" 2>/dev/null
done

echo ""
echo "✅ 缩图完成"
echo "   small: $SMALL ($(ls "$SMALL" | wc -l) 张)"
echo "   tiny:  $TINY ($(ls "$TINY" | wc -l) 张)"
echo "   xs:    $XS ($(ls "$XS" | wc -l) 张)"
echo ""
echo "下一步:"
echo "  vision_analyze(image_url='/tmp/img_tiny/<name>_tiny.jpg', question='...')"
echo "  或发 MEDIA:/tmp/img_tiny/<name>_tiny.jpg 给用户"
