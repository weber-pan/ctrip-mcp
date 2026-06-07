#!/usr/bin/env bash
# run.sh — 从 0 跑完整 ctrip-product-decision-deck 工作流
# 用法: ./scripts/run.sh <productId> <cityId> [pageCount]
# 例: ./scripts/run.sh 69762187 2 26
set -e
PRODUCT_ID="${1:-69762187}"
CITY_ID="${2:-2}"
PAGE_COUNT="${3:-26}"
VENV_PY="/opt/data/.venv/bin/python"
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DATA_DIR="/opt/data/ctrip-data"
PROJ_DIR="/opt/data/skills/ppt-master/skills/ppt-master/projects/cttrip_${PRODUCT_ID}_deck_$(date +%Y%m%d_%H%M%S)"

echo "================================================================"
echo "  携程产品决策手册 PPT - 从 0 走一遍"
echo "  productId=${PRODUCT_ID}  cityId=${CITY_ID}  pageCount=${PAGE_COUNT}"
echo "================================================================"

# Step 1: e2e 抓取 (ctrip-spa-capture)
echo "[Step 1] e2e 抓取 (ctrip-spa-capture)..."
if [ ! -f "${DATA_DIR}/xhr_ProductInfo_2nd_V3_h5_${PRODUCT_ID}.json" ]; then
  ${VENV_PY} /opt/data/skills/devops/ctrip-spa-capture/scripts/ctrip_spa_capture.py ${PRODUCT_ID} ${CITY_ID}
else
  echo "  [已存在] 跳过"
fi

# Step 1.1: 补 11 段被遗忘字段
echo "[Step 1.1] extract_more.py (补 11 段字段)..."
if [ ! -f "${DATA_DIR}/price_calendar_${PRODUCT_ID}.csv" ]; then
  ${VENV_PY} /opt/data/skills/devops/ctrip-spa-capture/scripts/extract_more.py ${PRODUCT_ID}
else
  echo "  [已存在] 跳过"
fi

# Step 1.2: shoppingid + getShoppingDetail (5 段真实酒店 + 航班)
echo "[Step 1.2] ctrip_shopping.py (5 段真实酒店 + 航班)..."
${VENV_PY} ${SKILL_DIR}/scripts/ctrip_shopping.py ${PRODUCT_ID} ${CITY_ID}

# Step 1.3: 7 日 DOM (图文行程)
echo "[Step 1.3] ctrip_dom_7days.py (7 日 DOM)..."
${VENV_PY} ${SKILL_DIR}/scripts/ctrip_dom_7days.py ${PRODUCT_ID} ${CITY_ID}

# Step 1.4: 全量图下载 (desc+poi+hotel+comment+competitor+ranking = 60+ 张)
echo "[Step 1.4] dl_all_imgs.py (60+ 张携程图)..."
if [ -f "${SKILL_DIR}/scripts/dl_all_imgs.py" ]; then
  ${VENV_PY} ${SKILL_DIR}/scripts/dl_all_imgs.py ${PRODUCT_ID}
else
  echo "  [!] 退路: 复用上次抓的 60+ 张图 (${DATA_DIR}/img_${PRODUCT_ID}/)"
fi

echo ""
echo "================================================================"
echo "  Step 1-1.4 完成. 数据在 ${DATA_DIR}/"
echo "  下一步: Step 2-7 走 ppt-master"
echo "================================================================"
