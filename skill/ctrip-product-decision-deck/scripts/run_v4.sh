#!/usr/bin/env bash
# run_v4.sh — v4 高质量决策手册 端到端
# 用法: ./scripts/run_v4.sh <productId> <cityId> <fromDate> <toDate> <travelers> <audience> [pageCount]
# 例:   ./scripts/run_v4.sh 69762187 2 2026-07-04 2026-07-10 "2 成人" "朋友/双人" 26

set -e
PRODUCT_ID="${1:-69762187}"
CITY_ID="${2:-2}"
FROM_DATE="${3:-2026-07-04}"
TO_DATE="${4:-2026-07-10}"
TRAVELERS="${5:-2 成人}"
AUDIENCE="${6:-朋友/双人}"
PAGE_COUNT="${7:-26}"

VENV_PY="/opt/data/.venv/bin/python"
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DATA_DIR="/opt/data/ctrip-data"
PROJ_DIR="/opt/data/skills/ppt-master/skills/ppt-master/projects/cttrip_${PRODUCT_ID}_v4_$(date +%Y%m%d_%H%M%S)"

echo "================================================================"
echo "  携程产品 v4 决策手册 - end-to-end"
echo "  productId=$PRODUCT_ID  cityId=$CITY_ID"
echo "  fromDate=$FROM_DATE  toDate=$TO_DATE"
echo "  travelers=$TRAVELERS  audience=$AUDIENCE"
echo "  pageCount=$PAGE_COUNT"
echo "================================================================"

# A 段 4 字段写入 spec
mkdir -p "$PROJ_DIR"
cat > "$PROJ_DIR/spec.yaml" <<EOF
project: cttrip_${PRODUCT_ID}_v4_$(date +%Y%m%d_%H%M%S)
canvas: ppt169
departCity: 上海 (city=$CITY_ID)
departDate: $FROM_DATE
returnDate: $TO_DATE
travelers: $TRAVELERS
audience: $AUDIENCE
duration: $(( ($(date -d "$TO_DATE" +%s) - $(date -d "$FROM_DATE" +%s)) / 86400 + 1 )) 日
pages: $PAGE_COUNT
date: $(date +%Y-%m-%d)
EOF
cat "$PROJ_DIR/spec.yaml"

# Step 1: e2e 抓取
echo "[Step 1] e2e 抓取 (ctrip-spa-capture)..."
if [ ! -f "${DATA_DIR}/xhr_ProductInfo_2nd_V3_h5_${PRODUCT_ID}.json" ]; then
  ${VENV_PY} /opt/data/skills/devops/ctrip-spa-capture/scripts/ctrip_spa_capture.py ${PRODUCT_ID} ${CITY_ID}
fi

# Step 1.1: 补 11 段
echo "[Step 1.1] extract_more.py (补字段)..."
if [ ! -f "${DATA_DIR}/price_calendar_${PRODUCT_ID}.csv" ]; then
  ${VENV_PY} /opt/data/skills/devops/ctrip-spa-capture/scripts/extract_more.py ${PRODUCT_ID}
fi

# Step 1.2: shoppingid + getShoppingDetail
echo "[Step 1.2] ctrip_shopping.py (5 段真实酒店 + 航班)..."
${VENV_PY} ${SKILL_DIR}/scripts/ctrip_shopping.py ${PRODUCT_ID} ${CITY_ID}

# Step 1.3: 7 日 DOM
echo "[Step 1.3] ctrip_dom_7days.py (7 日 DOM)..."
${VENV_PY} ${SKILL_DIR}/scripts/ctrip_dom_7days.py ${PRODUCT_ID} ${CITY_ID}

# Step 1.4: 全量图
echo "[Step 1.4] dl_all_imgs.py (60+ 张携程全量图)..."
${VENV_PY} ${SKILL_DIR}/scripts/dl_all_imgs.py ${PRODUCT_ID}

echo ""
echo "================================================================"
echo "  Step 1-1.4 完成. 数据集在 ${DATA_DIR}/"
echo "  下一步: 调 Hermes Agent 生成 PPT (用 spec.yaml 的 4 字段 + 60+ 图)"
echo "================================================================"
