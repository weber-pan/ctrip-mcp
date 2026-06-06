# 携程 m 端 h5 SPA graphql 接口抓取技术细节

**作者**: hermes agent · **测试日期**: 2026-06-05
**适用范围**: 携程 m 端 h5 SPA (`https://m.ctrip.com/webapp/vacations/tour/detail?productId=...`)

## 核心思路

携程 PC 端(`https://vacations.ctrip.com/travel/detail/...`)是 CSR 壳,curl 拿不到数据。
m 端 h5 SPA(`https://m.ctrip.com/webapp/vacations/tour/detail?productId=...&departCityId=2`)也是 CSR 壳,但**所有真实产品数据来自 SPA 内部 graphql/soa POST 请求**。

**挑战**:
1. `__INITIAL_STATE__` 是 `undefined` —— 壳 HTML 完全无数据
2. SPA 内部 fetch 调用路径被 webpack 压成 `t("xxx")` 短调用 —— 静态分析拿不到 endpoint
3. m 端 `__APP_SETTINGS__.context.restapi = "//sec-m.ctrip.com/restapi/soa2"`,但所有实际请求走 m.ctrip.com 域(不是 sec-m)
4. `page.on("response", cb)` 的 `resp.text()` 在 chromium devtools 协议下对**一次性流式 POST graphql** 拿不到 body(`body_len=0`)

**解法**:**在 `page.add_init_script` 阶段 hook `window.fetch` + `XMLHttpRequest.prototype.send`**,把响应 body 存到 `window.__captured`,最后 `page.evaluate("() => window.__captured")` 一次性取出。

## 完整 hook 模板

```python
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
```

**关键点**:
- `add_init_script` **在所有页面脚本前注入** —— 否则太晚,SPA 已缓存原 fetch
- `resp.clone().text()` 必须 **clone**,否则原 resp body 被消费,fetch 内部 promise 拿到空
- `__captured.push` 用 `__captured` 数组名(下划线开头)避免与 SPA 内部变量冲突
- `loadend` 事件比 `load` 稳 —— loadend 在 success/error/abort 都触发

## 已知携程 graphql queryName 清单(2026-06-05 实测)

| queryName | URL | 用途 | 产物大小 |
|---|---|---|---|
| `ProductInfo_1st_V3_h5` | `/restapi/soa2/18055/graphql` | 基础信息(首屏) | ~10KB |
| **`ProductInfo_2nd_V3_h5`** | 同上 | **核心数据(4 线路/酒店/点评/价格日历)—— 用这个** | **473KB** |
| `VPC_SelectDateProductInfo_h5` | 同上 | 选班期/选酒店/选航班 | 335KB |
| `ProductInfo_VisaInfo_h5` | 同上 | 签证信息 | 208KB |
| `batchPriceCalendar` | `/restapi/soa2/12433/batchPriceCalendar` | 价格日历 | 2KB |
| `getCommentSummary` | `/restapi/soa2/20047/getCommentSummary` | 点评汇总 | 6KB |
| `getByRelationId` | `/restapi/soa2/28181/json/getByRelationId` | 相关产品推荐 | 0.5KB |
| `getPromotionTag` | `/restapi/soa2/28181/json/getPromotionTag` | 促销标签 | 0.5KB |

**重点**:`_2nd_V3_h5` 已经包含 `_1st_V3_h5` 的全部字段 + 4 线路 + 8 酒店 + 价格日历,优先用这个。`_1st_V3_h5` 是首屏首包,数据精简,可能 0 命中(只在你等不及 2nd 时才需要)。

## Playwright 调用完整模板

```python
import os, time, json
from playwright.sync_api import sync_playwright

CHROMIUM = os.path.expanduser(
    "~/.cache/ms-playwright/chromium-1223/chrome-linux64/chrome"
)
# ↑ 这是 hermes 容器里现成的 chromium,不要再 npx playwright install

with sync_playwright() as p:
    browser = p.chromium.launch(
        executable_path=CHROMIUM,
        headless=True,
        args=["--no-sandbox", "--disable-blink-features=AutomationControlled",
              "--disable-dev-shm-usage"],
    )
    ctx = browser.new_context(
        user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                   "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
        viewport={"width": 390, "height": 844},
        device_scale_factor=3,
        is_mobile=True,
        has_touch=True,
        locale="zh-CN",
    )
    page = ctx.new_page()
    page.add_init_script(HOOK)  # ← 必须在 goto 前
    page.goto(URL, wait_until="domcontentloaded", timeout=60000)

    # 等产品标题出现
    try: page.wait_for_selector("text=沙巴", timeout=20000)
    except: pass

    time.sleep(3)
    # 滚动触发 lazy load
    for y in [0, 1000, 2000, 3000, 4000, 5000, 6000, 7000]:
        page.evaluate(f"window.scrollTo(0, {y})")
        time.sleep(1.5)
    time.sleep(3)

    captured = page.evaluate("() => window.__captured || []")
    browser.close()

# 按 URL 去重,保留首次
seen = {}
for c in captured:
    if c['url'] not in seen and len(c.get('body','')) > 100:
        seen[c['url']] = c
# 落盘
for url, c in seen.items():
    slug = ("graphql_" + url.split("queryName=")[-1].split("&")[0]
            if "queryName=" in url
            else url.split("/")[-1].split("?")[0])
    try:
        with open(f"/opt/data/ctrip-data/xhr_{slug}.json","w") as f:
            json.dump(json.loads(c['body']), f, ensure_ascii=False, indent=1)
    except:
        with open(f"/opt/data/ctrip-data/xhr_{slug}.txt","w") as f:
            f.write(c['body'])
```

## 5 个核心坑(踩过的)

### 坑 1:`resp.text()` 拿到空 body

**症状**:`on_response` 触发了 80 次,`resp.text()` 全部返回 `""`,`body_len=0`。
**原因**:chromium devtools 协议对一次性流式 POST 响应不保留 body(已被 fetch 内部消费)。
**修法**:不要用 `page.on("response", cb)` + `resp.text()`。改用 `add_init_script` hook 原始 `fetch`/`XHR`,在它们拿到 body 那一刻存下来。

### 坑 2:on_response handler 注册时机

**症状**:`page.goto` 之后才 `page.on("response", cb)`,结果 0 命中。
**原因**:SPA 内部 burst 请求在 goto 之后 50-200ms 内就发完了,handler 注册晚一步。
**修法**:
```python
page = ctx.new_page()
page.on("response", cb)   # 先注册
page.goto(URL)             # 再 goto
```

### 坑 3:`add_init_script` vs `evaluate`

**症状**:`page.evaluate("() => { window.fetch = hookedFetch }")` 注入,hook 不生效。
**原因**:SPA 内部 `import` 的 fetch 在 evaluate 之前已 cached;evaluate 改的是 window.fetch,**但 SPA 内部用的是 imported binding**。
**修法**:**`add_init_script`** 在 SPA 任何脚本前注入,改写 `window.fetch`,而 SPA 内部 `import` 的 fetch 在脚本第一行就是 `window.fetch(...)` 时会被 hook 住(Web Fetch 规范要求 internal slot 走原 fetch,但用户代码走 window.fetch 引用)。

### 坑 4:容器没 chrome,`npx playwright install` 又装不上

**症状**:`npx playwright install chrome` 报 "Failed to install chrome / Password: su: Authentication failure"。
**原因**:容器 uid=10000 无 sudo,playwright install 要 root 装系统依赖。
**修法**:用 `~/.cache/ms-playwright/chromium-1223/chrome-linux64/chrome` 这个**已经存在的 chromium** 路径(在 hermes 容器里,首次安装 agent-browser 的时候下载过),传给 `executable_path=CHROMIUM`。

```python
import os
CHROMIUM = os.path.expanduser(
    "~/.cache/ms-playwright/chromium-1223/chrome-linux64/chrome"
)
print("exists:", os.path.exists(CHROMIUM))  # True
```

如果 `executable_path` 也不存在,降级到 `chromium_headless_shell-1223`:
```python
CHROMIUM = os.path.expanduser(
    "~/.cache/ms-playwright/chromium_headless_shell-1223/chrome-headless-shell-linux64/chrome-headless-shell"
)
```

### 坑 5:SPA lazy load,滚动不到就拿不到完整数据

**症状**:`_2nd_V3_h5` 返回数据不全(缺 D3-D6 行程 / 缺后半截酒店)。
**原因**:携程 SPA 按需 lazy load 接口,滚到底部才会触发 2nd_V3 完整包。
**修法**:
```python
for y in [0, 1000, 2000, 3000, 4000, 5000, 6000, 7000]:
    page.evaluate(f"window.scrollTo(0, {y})")
    time.sleep(1.5)
```

## 已知 m 端接口 base URL

- `https://m.ctrip.com/restapi/soa2/<id>/<method>`(主)
- `https://sec-m.ctrip.com/restapi/soa2/<id>/<method>`(浮层/GetFloatUI 等)
- `https://www.trip.com/restapi/soa2/...`(ubt/anti-bot 类)
- `https://ins-m.ctripins.com/restapi/soa2`(保险,跟度假产品无关)

**直调 0 鉴权会 403**,原因是:
- 必须带 `_fxpcqlniredt` cookie(anti-bot 用的固定 cookie,值是数字时间戳)
- 必须带 `x-traceID` 头
- 必须有正确 `head.cid/ctok/cver/lang/sid/syscode/auth` 字段

**所以别直调,跑真浏览器最稳**。

## 完整可复用脚本

见同目录 `scripts/ctrip_spa_capture.py`。一行命令:

```bash
/opt/hermes/.venv/bin/python /opt/data/skills/devops/ctrip-product-research/scripts/ctrip_spa_capture.py 64158367 2
# 产物: /opt/data/ctrip-data/xhr_*.json (7 个,1MB+) + m_64158367_full.png (8MB 全页截图) + m_64158367_top.png + dom_text.txt
```

## 验证清单(真抓成功 = 5 个文件都存在)

```bash
ls -la /opt/data/ctrip-data/xhr_*.json
# 期望看到:
# xhr_graphql_ProductInfo_2nd_V3_h5.json  (~470KB)
# xhr_graphql_VPC_SelectDateProductInfo_h5.json  (~330KB)
# xhr_graphql_ProductInfo_VisaInfo_h5.json  (~200KB)
# xhr_batchPriceCalendar.json  (~2KB)
# xhr_getCommentSummary.json  (~6KB)
# xhr_getByRelationId.json  (~0.5KB)
# xhr_getPromotionTag.json  (~0.5KB)
```

最少前 3 个存在,报告就够用了。
