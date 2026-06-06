# CSR SPA 真实数据抓取技术(generalizable)

> 来源:2026-06-05/06 携程 m 端 h5 SPA 抓取经验,可推广到任何 SPA 站点(微博/小红书/抖音/美团)。

## 一句话总结

**用 `add_init_script` 在页面脚本执行前 hook `window.fetch` + `XMLHttpRequest.send`**,把响应 body 存到 `window.__captured`,跑完浏览器后一次性 `page.evaluate` 读出。

## 适用场景

- 任何 CSR 单页应用(Next.js / Taro / 自研 SPA)
- 浏览器渲染后才有数据,curl 拿到的是空壳
- 不在 mcp hub 里的非主流站
- 想拿"真实返回结构"而不是 wendao 二次复述

## 完整模板

```python
HOOK = r"""
window.__captured = [];
const _fetch = window.fetch;
window.fetch = async function(input, init) {
  const u = typeof input === 'string' ? input : input.url;
  const r = await _fetch.apply(this, arguments);
  try {
    const c = r.clone();
    const t = await c.text();
    if (/graphql|soa2|product|hotel|flight/i.test(u)) {
      window.__captured.push({u, body: t, ts: Date.now()});
    }
  } catch(e) {}
  return r;
};
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
      if (/graphql|soa2|product|hotel|flight/i.test(u)) {
        window.__captured.push({u, body: this.responseText, ts: Date.now()});
      }
    } catch(e) {}
  });
  return _xsend.apply(this, arguments);
};
"""

from playwright.async_api import async_playwright
import json, time, os

async def capture_spa(url, out_dir, scroll=True, timeout=60, headless=True):
    out_dir = os.path.abspath(out_dir); os.makedirs(out_dir, exist_ok=True)
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=headless,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled", "--disable-dev-shm-usage"],
        )
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15",
            viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, locale="zh-CN",
        )
        page = await ctx.new_page()
        await page.add_init_script(HOOK)  # 必须在 page.goto 之前
        await page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
        if scroll:
            for y in [0, 1000, 2000, 3000, 4000, 5000]:
                await page.evaluate(f"window.scrollTo(0, {y})")
                await page.wait_for_timeout(1200)
        dom = await page.evaluate("() => document.body.innerText")
        png = await page.screenshot(full_page=True)
        captured = await page.evaluate("() => { const c = window.__captured || []; window.__captured = []; return c; }")
        await browser.close()
    saved = {}
    for c in captured:
        try: body = json.loads(c["body"])
        except: body = c["body"]
        tag = url_to_tag(c["u"])
        if not tag: continue
        fn = os.path.join(out_dir, f"xhr_{tag}.json")
        with open(fn, "w") as f: json.dump(body, f, ensure_ascii=False, indent=1)
        saved[tag] = fn
    with open(os.path.join(out_dir, "dom.txt"), "w") as f: f.write(dom)
    with open(os.path.join(out_dir, "full.png"), "wb") as f: f.write(png)
    return {"saved": saved, "xhrs_count": len(captured)}

def url_to_tag(url):
    import re
    from urllib.parse import urlparse
    m = re.search(r'queryName=([A-Za-z0-9_]+)', url)
    if m: return m.group(1)
    p = urlparse(url); last = p.path.rstrip('/').split('/')[-1]
    return last if last and last != "graphql" else None
```

## 5 个关键坑(实战踩过)

1. **`add_init_script` 必须在 `page.goto` 之前** — 否则 SPA 内部已缓存原 fetch,hook 太晚
2. **不要用 `page.on("response", cb)` 拿 body** — chromium devtools 协议对一次性流式 POST 拿不到 body(`resp.text()` 返回空)。**用 hook 拿 body 是唯一可靠路径**
3. **fetch hook 完还要 XHR hook** — 老代码混用 XHR/SPA
4. **graphql 端点是统一的** — 真实 method 名在 `?queryName=XXX` 里,URL 末尾是字面 "graphql"。要正则提 queryName
5. **要滚动到底部** — SPA 用 lazy load,不滚只拿到 D1-D2,后续 graphql 不返回

## 推广到其他 SPA

| 站点 | URL 模式 | method 提取 | 数据规模 |
|---|---|---|---|
| 携程 m 端 h5 | `m.ctrip.com/restapi/soa2/<id>/graphql?queryName=ProductInfo_2nd_V3_h5` | queryName | ~470KB/产品 |
| 携程 m 端 老 | `sec-m.ctrip.com/restapi/soa2/<id>/json/<MethodName>` | 路径末尾 | 同 |
| 微博 m 端 | `m.weibo.cn/api/...` | 路径末尾 | 几百 KB |
| 小红书 web | `xiaohongshu.com/api/sns/web/v2/...` | 路径末尾 | 几百 KB (强反爬) |
| 美团 m 端 | `i.meituan.com/ptravel/...` | 路径末尾 | 中 |

**反爬严重度排序**(从弱到强):
- 携程 m 端 ← 容易(可裸抓)
- 美团 ← 中(可能要 cookie)
- 微博 ← 难(频繁 412/403)
- 小红书 ← 极难(指纹+cookie+验证码,基本只能付费 API)

## 跟 wendao / 商业 API 的对比

| 路径 | 速度 | 准确度 | 反爬 | 适合 |
|---|---|---|---|---|
| **CSR SPA hook** | ~25s/产品 | ⭐⭐⭐⭐⭐ | 中 | 已知产品号,真数据 |
| wendao LLM | 10-30s/query | ⭐⭐⭐(串台) | 无 | 兜底,自然语言 |
| 商业爬虫 API | 1-3s/产品 | ⭐⭐⭐⭐ | 已处理 | 大量产品批量 |

## 与姊妹项目 ctrip-mcp 的关系

- `ctrip-product-research` skill: 工作流 + 通用技术(给 Hermes Agent 内部用)
- `ctrip-mcp` gitee repo(https://gitee.com/weber-pan/ctrip-mcp): 把这个技术封装成 MCP server(给所有 MCP 客户端用)
- 两个互补,选哪个看部署形态。
