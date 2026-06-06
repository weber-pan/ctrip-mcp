#!/usr/bin/env python3
"""
携程 m 端 h5 SPA graphql/soa 抓取脚本 (2026-06-05)

用法:
    # 单 productId 抓(原始用法,产物 xhr_<id>_*.json + dom_text.txt)
    /opt/hermes/.venv/bin/python ctrip_spa_capture.py <productId> <departCityId>

    # 批量 sub-product 抓(2026-06-05 加,产物 xhr_<tag>_*.json + dom_<tag>.txt)
    /opt/hermes/.venv/bin/python ctrip_spa_capture.py --multi "main,id1,id2,id3" <departCityId>

    # 例: 沙巴 4 条线批量抓
    /opt/hermes/.venv/bin/python ctrip_spa_capture.py --multi "64158367,38789419,73810124,73810123" 2

产物(全部落 /opt/data/ctrip-data/):
    单 productId 模式:
        - xhr_graphql_ProductInfo_2nd_V3_h5.json  (核心数据, ~470KB)
        - xhr_graphql_VPC_SelectDateProductInfo_h5.json  (班期, ~330KB)
        - xhr_graphql_ProductInfo_VisaInfo_h5.json  (签证, ~200KB)
        - xhr_batchPriceCalendar.json
        - xhr_getCommentSummary.json
        - xhr_getByRelationId.json
        - xhr_getPromotionTag.json
        - m_<id>_full.png  (整页截图, ~8MB)
        - m_<id>_top.png  (首屏截图, ~2.5MB)
        - dom_text.txt  (document.body.innerText, ~15KB)

    批量模式(--multi):
        - 第一个 id 的产物走 xhr_*.json 单文件命名
        - 后续 id 的产物走 xhr_<id>_*.json + dom_<id>.txt(避免覆盖)

依赖:
    pip install playwright
    chromium 在 ~/.cache/ms-playwright/chromium-1223/chrome-linux64/chrome 现成
    (不要 npx playwright install,容器没 root)
"""
import os, sys, time, json
from playwright.sync_api import sync_playwright

OUT = "/opt/data/ctrip-data"
CHROMIUM = os.path.expanduser(
    "~/.cache/ms-playwright/chromium-1223/chrome-linux64/chrome"
)
# fallback 到 headless shell
if not os.path.exists(CHROMIUM):
    CHROMIUM = os.path.expanduser(
        "~/.cache/ms-playwright/chromium_headless_shell-1223/chrome-headless-shell-linux64/chrome-headless-shell"
    )

# 抓取目标 URL 模式
TARGET_PATTERNS = (
    "graphql", "batchPriceCalendar", "getCommentSummary",
    "getByRelationId", "getPromotionTag", "ProductInfo", "VPC_",
)

# 关键 hook:在所有页面脚本前注入,劫持 fetch + XHR
HOOK = """
window.__captured = [];
const _fetch = window.fetch;
window.fetch = async function(input, init) {
  const url = typeof input === 'string' ? input : input.url;
  const method = (init && init.method) || (input && input.method) || 'GET';
  const resp = await _fetch.apply(this, arguments);
  try {
    const clone = resp.clone();
    const text = await clone.text();
    if (/graphql|batchPriceCalendar|getCommentSummary|getByRelationId|getPromotionTag|ProductInfo|VPC_/.test(url)) {
      window.__captured.push({url, method, status: resp.status, body: text});
    }
  } catch(e) {}
  return resp;
};
const _open = XMLHttpRequest.prototype.open;
const _send = XMLHttpRequest.prototype.send;
XMLHttpRequest.prototype.open = function(method, url) { this.__u = url; this.__m = method; return _open.apply(this, arguments); };
XMLHttpRequest.prototype.send = function(body) {
  this.addEventListener('loadend', () => {
    try {
      if (/graphql|batchPriceCalendar|getCommentSummary|getByRelationId|getPromotionTag|ProductInfo|VPC_/.test(this.__u || '')) {
        window.__captured.push({url: this.__u, method: this.__m, status: this.status, body: this.responseText});
      }
    } catch(e) {}
  });
  return _send.apply(this, arguments);
};
"""


def capture(product_id: str, depart_city_id: str, tag: str = None) -> dict:
    """跑真浏览器抓 SPA 数据,返回保存路径摘要

    tag: 如果提供,产物落 dom_<tag>.txt + xhr_<tag>_*.json(用于多 productId 批量抓)
    """
    os.makedirs(OUT, exist_ok=True)
    url = (f"https://m.ctrip.com/webapp/vacations/tour/detail"
           f"?productId={product_id}&departCityId={depart_city_id}")

    if not os.path.exists(CHROMIUM):
        sys.exit(f"❌ chromium not found at {CHROMIUM}\n"
                 f"   fallback paths also tried. install with: "
                 f"/opt/hermes/.venv/bin/pip install playwright")

    # 文件名模板
    if tag:
        dom_fn = f"{OUT}/dom_{tag}.txt"
        top_png = f"{OUT}/m_{tag}_top.png"
        full_png = f"{OUT}/m_{tag}_full.png"
        # xhr 文件名加 tag 前缀(避免多次抓覆盖)
        xhr_prefix = f"xhr_{tag}_"
    else:
        dom_fn = f"{OUT}/dom_text.txt"
        top_png = f"{OUT}/m_{product_id}_top.png"
        full_png = f"{OUT}/m_{product_id}_full.png"
        xhr_prefix = "xhr_"

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=CHROMIUM,
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
            ],
        )
        ctx = browser.new_context(
            user_agent=("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                        "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"),
            viewport={"width": 390, "height": 844},
            device_scale_factor=3,
            is_mobile=True, has_touch=True, locale="zh-CN",
        )
        page = ctx.new_page()
        page.add_init_script(HOOK)  # 必须在 goto 前
        print(f"[{tag or 'main'}] navigating to {url}", flush=True)
        page.goto(url, wait_until="domcontentloaded", timeout=60000)

        # 等产品标题或目的地下文出现(宽松一点,任意字符)
        try:
            page.wait_for_selector("text=沙巴", timeout=20000)
        except Exception:
            pass
        time.sleep(3)

        # 滚动触发 SPA lazy load
        for y in [0, 1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000]:
            page.evaluate(f"window.scrollTo(0, {y})")
            time.sleep(1.5)
        time.sleep(3)

        # 抓 DOM 文本 + 截图
        dom_text = page.evaluate("() => document.body.innerText")
        page.screenshot(path=top_png, full_page=False)
        page.screenshot(path=full_png, full_page=True)

        # 取出 hook 抓到的 body
        captured = page.evaluate("() => window.__captured || []")
        browser.close()

    # 去重(同 URL 取首)
    seen = {}
    for c in captured:
        if not c.get('body') or len(c['body']) < 50:
            continue
        if c['url'] not in seen:
            seen[c['url']] = c
    print(f"[{tag or 'main'}] captured in-page: {len(captured)}, unique: {len(seen)}", flush=True)

    # 落盘
    saved = []
    for url, c in seen.items():
        if "queryName=" in url:
            slug = "graphql_" + url.split("queryName=")[-1].split("&")[0]
        else:
            slug = url.split("/")[-1].split("?")[0]
        try:
            j = json.loads(c['body'])
            fn = f"{OUT}/{xhr_prefix}{slug}.json"
            with open(fn, "w") as f:
                json.dump(j, f, ensure_ascii=False, indent=1)
            saved.append((fn, len(c['body'])))
        except Exception:
            fn = f"{OUT}/{xhr_prefix}{slug}.txt"
            with open(fn, "w") as f:
                f.write(c['body'])
            saved.append((fn, len(c['body'])))

    # 落 DOM 文本
    with open(dom_fn, "w") as f:
        f.write(dom_text)

    return {
        "url": url,
        "tag": tag or "main",
        "captured_total": len(captured),
        "unique": len(seen),
        "saved_files": saved,
        "dom": dom_fn,
        "top_png": top_png,
        "full_png": full_png,
    }


if __name__ == "__main__":
    if "--multi" in sys.argv:
        # 批量模式: --multi "id1,id2,id3" <deptCity>
        i = sys.argv.index("--multi")
        ids = sys.argv[i + 1].split(",")
        if len(sys.argv) < i + 3:
            sys.exit("用法: ctrip_spa_capture.py --multi \"id1,id2,id3\" <deptCity>")
        dcid = sys.argv[i + 2]
        results = []
        for idx, pid in enumerate(ids):
            # 第一个走 tag=None(产物用 xhr_*.json + dom_text.txt)
            # 后续走 tag="B/C/D_<id>"(产物用 xhr_<tag>_*.json + dom_<tag>.txt)
            if idx == 0:
                tag = None
            else:
                # 默认用 A/B/C/D 标签(A=主产品)
                letters = ["A", "B", "C", "D", "E", "F", "G", "H"]
                tag = f"{letters[idx]}_{pid}"
            r = capture(pid.strip(), dcid, tag=tag)
            results.append(r)
            print(f"\n=== {r['tag']} SAVED ===")
            for fn, sz in r['saved_files']:
                print(f"  {os.path.basename(fn):50s}  {sz:>8} B")
            print(f"  DOM: {r['dom']}\n  Top: {r['top_png']}\n  Full: {r['full_png']}\n")
        print(f"\n=== TOTAL: {len(results)} products captured ===")
    else:
        if len(sys.argv) < 3:
            sys.exit("用法:\n"
                     "  单 productId: ctrip_spa_capture.py <productId> <deptCity>\n"
                     "  批量:         ctrip_spa_capture.py --multi \"id1,id2,id3\" <deptCity>\n"
                     "\n例:\n"
                     "  ctrip_spa_capture.py 64158367 2\n"
                     "  ctrip_spa_capture.py --multi \"64158367,38789419,73810124,73810123\" 2")
        pid = sys.argv[1]
        dcid = sys.argv[2]
        result = capture(pid, dcid)
        print("\n=== SAVED ===")
        for fn, sz in result["saved_files"]:
            print(f"  {os.path.basename(fn):50s}  {sz:>8} B")
        print(f"\nDOM text: {result['dom']}")
        print(f"Top screenshot: {result['top_png']}")
        print(f"Full screenshot: {result['full_png']}")
