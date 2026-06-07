"""
ctrip-mcp capture core
~~~~~~~~~~~~~~~~~~~~~~~

携程 m 端 h5 SPA 抓取核心:
- Playwright + chromium 跑真实 SPA
- fetch + XHR hook 拦截 graphql/soa body
- DOM 文本 + 截图 落盘

设计原则:
- 零 token (抓的是公开接口,无鉴权)
- 一次抓取 = 8 个核心接口 + DOM + 截图
- sub-product 二次抓 = 补 B/C/D 行程
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

# 关键: hook 注入必须在所有页面脚本前
HOOK = r"""
window.__captured = [];
const _fetch = window.fetch;
window.fetch = async function(input, init) {
  const u = typeof input === 'string' ? input : input.url;
  const r = await _fetch.apply(this, arguments);
  try {
    const c = r.clone();
    const t = await c.text();
    if (/graphql|batchPriceCalendar|getCommentSummary|getByRelationId|getPromotionTag|VPC_|ProductInfo|VisaInfo/i.test(u)) {
      window.__captured.push({u, body: t, ts: Date.now()});
    }
  } catch(e) {}
  return r;
};
// XHR 兜底(SPA 老代码可能用 XHR)
const _xopen = XMLHttpRequest.prototype.open;
XMLHttpRequest.prototype.open = function(method, url) {
  this.__url = url;
  return _xopen.apply(this, arguments);
};
const _xsend = XMLHttpRequest.prototype.send;
XMLHttpRequest.prototype.send = function(body) {
  this.addEventListener('loadend', () => {
    try {
      const u = this.__url || '';
      if (/graphql|batchPriceCalendar|getCommentSummary|getByRelationId|getPromotionTag|VPC_|ProductInfo|VisaInfo/i.test(u)) {
        window.__captured.push({u, body: this.responseText, ts: Date.now()});
      }
    } catch(e) {}
  });
  return _xsend.apply(this, arguments);
};
"""


def find_chromium() -> str:
    """自动探测 chromium 路径"""
    candidates = [
        os.environ.get("CTRIP_CHROMIUM"),
        os.path.expanduser("~/.cache/ms-playwright/chromium-1223/chrome-linux64/chrome"),
        os.path.expanduser("~/.cache/ms-playwright/chromium_headless_shell-1223/chrome-headless-shell-linux64/chrome-headless-shell"),
    ]
    for p in candidates:
        if p and Path(p).exists():
            return p
    import glob
    for pattern in [
        os.path.expanduser("~/.cache/ms-playwright/chromium*/chrome-linux*/chrome"),
        os.path.expanduser("~/.cache/ms-playwright/chromium*/chrome-headless-shell-linux*/chrome-headless-shell"),
    ]:
        matches = glob.glob(pattern)
        if matches:
            return matches[0]
    raise FileNotFoundError(
        "chromium not found. Run: playwright install chromium"
    )


async def spa_capture(
    product_id: int,
    depart_city_id: int = 2,
    data_dir: str | None = None,
    timeout: int = 60,
    scroll: bool = True,
) -> dict[str, Any]:
    """
    抓取携程 m 端 h5 SPA 真实 graphql/soa body

    Args:
        product_id: 携程产品号, 如 64158367
        depart_city_id: 出发城市, 2=上海
        data_dir: 产物落盘目录, 默认 /opt/data/ctrip-data/
        timeout: 超时秒
        scroll: 是否滚动触发 lazy load

    Returns:
        {
            "product_id": int,
            "xhrs": [{url, ts}, ...],
            "saved": {tag: filepath, ...},
            "duration_s": float,
        }
    """
    from playwright.async_api import async_playwright

    data_dir = Path(data_dir or os.environ.get("CTRIP_DATA_DIR", "/opt/data/ctrip-data"))
    data_dir.mkdir(parents=True, exist_ok=True)
    chromium = find_chromium()
    url = f"https://m.ctrip.com/webapp/vacations/tour/detail?productId={product_id}&departCityId={depart_city_id}"

    t0 = time.time()
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            executable_path=chromium,
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
            ],
        )
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148",
            viewport={"width": 390, "height": 844},
            device_scale_factor=3,
            is_mobile=True,
            has_touch=True,
            locale="zh-CN",
        )
        page = await ctx.new_page()
        await page.add_init_script(HOOK)
        await page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
        try:
            await page.wait_for_selector("text=沙巴", timeout=20000)
        except Exception:
            pass
        if scroll:
            for y in [0, 1000, 2000, 3000, 4000, 5000]:
                await page.evaluate(f"window.scrollTo(0, {y})")
                await page.wait_for_timeout(1200)
        dom = await page.evaluate("() => document.body.innerText")
        png = await page.screenshot(full_page=True)
        captured = await page.evaluate("() => { const c = window.__captured || []; window.__captured = []; return c; }")
        await browser.close()

    # 落盘
    saved = {}
    for c in captured:
        try:
            body = json.loads(c["body"])
        except Exception:
            body = c["body"]
        tag = _url_to_tag(c["u"])
        if not tag:
            continue
        # 主文件名
        fn = data_dir / f"xhr_{tag}.json"
        if fn.exists():
            fn = data_dir / f"xhr_{tag}_{product_id}.json"
        with open(fn, "w") as f:
            json.dump(body, f, ensure_ascii=False, indent=1)
        saved[tag] = str(fn)

    dom_fn = data_dir / f"dom_{product_id}.txt"
    with open(dom_fn, "w") as f:
        f.write(dom)
    saved["dom"] = str(dom_fn)

    png_fn = data_dir / f"m_{product_id}_full.png"
    with open(png_fn, "wb") as f:
        f.write(png)
    saved["screenshot"] = str(png_fn)

    return {
        "product_id": product_id,
        "xhrs": [{"url": c["u"], "ts": c["ts"]} for c in captured],
        "saved": saved,
        "duration_s": round(time.time() - t0, 2),
    }


def _url_to_tag(url: str) -> str | None:
    """从 URL 提取 tag 标识
    例:
      /restapi/soa2/18055/graphql?queryName=ProductInfo_2nd_V3_h5  ->  ProductInfo_2nd_V3_h5
      /restapi/soa2/14666/json/ProductInfo_2nd_V3_h5                ->  ProductInfo_2nd_V3_h5
      /restapi/batchPriceCalendar                                    ->  batchPriceCalendar
    """
    m = re.search(r'queryName=([A-Za-z0-9_]+)', url)
    if m:
        return m.group(1)
    parsed = urlparse(url)
    last = parsed.path.rstrip('/').split('/')[-1]
    if last and last != "graphql":
        return last
    return None


def _find_file(data_dir: Path, tag: str, product_id: int | None = None) -> Path | None:
    """智能找文件: 新名优先, 老名兜底, 带 _pid 后缀"""
    names = []
    if product_id is not None:
        names.append(f"xhr_{tag}_{product_id}.json")
    names.append(f"xhr_{tag}.json")
    for n in names:
        f = data_dir / n
        if f.exists():
            return f
    return None


def parse_daily_min_prices(product_id: int, data_dir: str | None = None) -> dict[str, Any]:
    """
    解析 dailyMinPrices (优先用 VPC 接口,日期格式友好)

    Returns:
        {
            "dates": ["2026-06-08", "2026-06-09", ...],
            "by_date": {
                "2026-07-04": [
                    {"productId": 64158367, "price": 6858, "lineName": "A线"},
                    ...
                ],
                ...
            },
            "min_price_overall": {date, productId, price, lineName}
        }
    """
    data_dir = Path(data_dir or os.environ.get("CTRIP_DATA_DIR", "/opt/data/ctrip-data"))
    # 优先 VPC (date 字段是 string "2026-06-08")
    f = _find_file(data_dir, "VPC_SelectDateProductInfo_h5", product_id)
    if not f:
        # 退路: 2nd_V3 (hotelDate 是 /Date(ms+0800)/)
        f = _find_file(data_dir, "ProductInfo_2nd_V3_h5", product_id)
    if not f:
        raise FileNotFoundError(f"no product data in {data_dir}")

    j = json.load(open(f))
    pi = j["data"]["productInfo"]

    # 4 条线路名 - 从 TourGroupInfo 或 groupCard 拿
    line_names = {}
    tgi = (pi.get("TourGroupInfo") or {}).get("TourGroupProductInfo") or []
    for t in tgi:
        line_names[t.get("ProductId")] = t.get("Description", "?")
    if not line_names:
        for c in (pi.get("groupCard") or {}).get("cards") or []:
            line_names[c.get("productId")] = c.get("name", "?")

    by_date = {}
    daily = pi.get("priceCalendar", {}).get("dailyMinPrices", [])
    for d in daily:
        # 两种日期格式
        date = d.get("date") or _parse_net_date(d.get("hotelDate"))
        if not date:
            continue
        prices = []
        # VPC 格式: d.productId(主) + d.productPrices[](其他)
        main_pid = d.get("productId")
        if main_pid is not None and d.get("price") is not None:
            prices.append({
                "productId": main_pid,
                "price": d.get("price"),
                "lineName": line_names.get(main_pid, "?"),
            })
        for pp in d.get("productPrices", []):
            pid2 = pp.get("productId")
            if pid2 is None or pid2 == main_pid:
                continue
            prices.append({
                "productId": pid2,
                "price": pp.get("price"),
                "lineName": line_names.get(pid2, "?"),
            })
        by_date[date] = prices

    # 全月最低
    flat = [(d, p) for d, lst in by_date.items() for p in lst if p.get("price") is not None]
    if flat:
        best = min(flat, key=lambda x: x[1]["price"] or 9e9)
        min_overall = {"date": best[0], **best[1]}
    else:
        min_overall = None
    return {
        "dates": sorted(by_date.keys()),
        "by_date": by_date,
        "min_price_overall": min_overall,
    }


def _parse_net_date(s: str | None) -> str | None:
    """解析 '/Date(1782230400000+0800)/' -> '2026-06-24'"""
    if not s or not isinstance(s, str):
        return None
    m = re.search(r"/Date\((\d+)", s)
    if not m:
        return None
    from datetime import datetime, timezone, timedelta
    ms = int(m.group(1))
    # 用 +0800 时区
    tz = timezone(timedelta(hours=8))
    dt = datetime.fromtimestamp(ms / 1000, tz=tz)
    return dt.strftime("%Y-%m-%d")
