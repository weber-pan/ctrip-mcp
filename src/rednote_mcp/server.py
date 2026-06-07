"""rednote-mcp server — 适配 mcp SDK 1.27+ stdio_server 新签名。

登录模式:
- **cookie 注入 (推荐)**: 
  - 方式 A: `REDNOTE_COOKIES` env — 原始 JSON 字符串 (mcphub 配, 重启即更新)
  - 方式 B: `REDNOTE_COOKIES_FILE` env — JSON 文件路径 (向后兼容)
- **QR 扫码 (兜底)**: headless 弹登录 → ASCII QR 打印 → 用户扫码

mcphub 使用: 改 env → 重启服务 → 新 cookie 自动生效
"""
import asyncio
import os
import sys
import json
import base64
import re
from typing import Any
from io import BytesIO
from datetime import datetime
from playwright.async_api import async_playwright
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# ==================== 配置 ====================
BROWSER_DATA_DIR = os.environ.get(
    "REDNOTE_BROWSER_DIR",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "browser_data")
)
HEADLESS = os.environ.get("REDNOTE_HEADLESS", "true").lower() in ("1", "true", "yes")
COOKIES_FILE = os.environ.get("REDNOTE_COOKIES_FILE", "/opt/data/.secrets/xhs_cookies.json")
COOKIES_RAW = os.environ.get("REDNOTE_COOKIES", "")  # mcphub 直配: 原始 JSON 字符串
LOGIN_TIMEOUT_S = int(os.environ.get("REDNOTE_LOGIN_TIMEOUT", "180"))
XHS_DOMAIN = "https://www.xiaohongshu.com"
DESKTOP_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

os.makedirs(BROWSER_DATA_DIR, exist_ok=True)

# ==================== 全局状态 ====================
playwright_instance = None
browser_context = None
main_page = None
is_logged_in = False
cookie_injected = False

app = Server("rednote-mcp")


# ==================== QR ASCII 渲染 ====================
def render_qr_ascii(png_bytes: bytes, width: int = 40) -> str:
    try:
        from PIL import Image
        img = Image.open(BytesIO(png_bytes)).convert("1")
        w, h = img.size
        new_h = max(8, int(h * width / w / 2))
        img = img.resize((width, new_h), Image.NEAREST)
        pixels = img.load()
        return "\n".join(
            "".join("  " if pixels[x, y] else "██" for x in range(width))
            for y in range(new_h)
        )
    except ImportError:
        return "[qrcode/PIL 未装]"


# ==================== 浏览器 + cookie 管理 ====================
async def ensure_browser():
    """启动浏览器, 注入 cookie (REDNOTE_COOKIES > REDNOTE_COOKIES_FILE > 扫码)。"""
    global playwright_instance, browser_context, main_page, is_logged_in, cookie_injected
    if browser_context is None:
        playwright_instance = await async_playwright().start()
        browser_context = await playwright_instance.chromium.launch_persistent_context(
            user_data_dir=BROWSER_DATA_DIR,
            headless=HEADLESS,
            viewport={"width": 1280, "height": 800},
            user_agent=DESKTOP_UA,
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
            timeout=60000,
        )
        if browser_context.pages:
            main_page = browser_context.pages[0]
        else:
            main_page = await browser_context.new_page()
        main_page.set_default_timeout(60000)

    # 注入 cookie (mcphub 重启 = 新进程 + 新 env, 所以只注入一次)
    if not cookie_injected:
        cookies = None
        # 优先级 1: REDNOTE_COOKIES (env 直配, 兼容 JSON array + cookie string)
        if COOKIES_RAW:
            from rednote_mcp.xhs_core import _parse_cookie_source as _parse_xhs
            cookies = _parse_xhs(COOKIES_RAW)
            if cookies:
                print(f"[rednote-mcp] 从 REDNOTE_COOKIES 解析 {len(cookies)} cookies", file=sys.stderr)
            else:
                print(f"[rednote-mcp] REDNOTE_COOKIES 无法解析 (需 JSON array 或 name=value; name2=value2)", file=sys.stderr)
        # 优先级 2: REDNOTE_COOKIES_FILE (文件路径, 向后兼容)
        if not cookies and os.path.exists(COOKIES_FILE):
            try:
                with open(COOKIES_FILE) as f:
                    cookies = json.load(f)
                print(f"[rednote-mcp] 从 REDNOTE_COOKIES_FILE 读取 {len(cookies)} cookies", file=sys.stderr)
            except Exception as e:
                print(f"[rednote-mcp] REDNOTE_COOKIES_FILE 读取失败: {e}", file=sys.stderr)
        if cookies and len(cookies) >= 5:
            await browser_context.add_cookies(cookies)
            cookie_injected = True
            print(f"[rednote-mcp] 注入 {len(cookies)} cookies ✅", file=sys.stderr)

    # 验证登录态
    if not is_logged_in:
        try:
            await main_page.goto(f"{XHS_DOMAIN}/explore", timeout=30000, wait_until="domcontentloaded")
        except Exception:
            pass
        await asyncio.sleep(3)
        title = await main_page.title()
        url = main_page.url
        if "error_code=300012" in url or "安全限制" in title or "页面不见了" in title:
            is_logged_in = False
        else:
            is_logged_in = cookie_injected
    return is_logged_in


async def trigger_login_qr_scan() -> dict:
    """二维码扫码登录 (兜底)"""
    global is_logged_in
    await main_page.goto(f"{XHS_DOMAIN}", timeout=30000, wait_until="domcontentloaded")
    await asyncio.sleep(2)
    # 找登录入口
    login_btns = await main_page.query_selector_all('text="登录"')
    if login_btns:
        try:
            await login_btns[0].click()
        except Exception:
            pass
    await asyncio.sleep(3)
    # 找 QR
    qr_el = await main_page.query_selector('.qrcode-img, [class*="qrcode"]')
    if not qr_el:
        all_imgs = await main_page.query_selector_all('img')
        for img in all_imgs:
            box = await img.bounding_box()
            if box and 100 < box['width'] < 200 and 100 < box['height'] < 200:
                qr_el = img
                break
    if not qr_el:
        return {"status": "fail", "error": "未找到登录二维码,可能 IP 被风控无法打开登录页"}
    qr_src = await qr_el.get_attribute("src")
    if qr_src and qr_src.startswith("data:image"):
        m = re.match(r"data:image/\w+;base64,(.+)", qr_src)
        if m:
            png_bytes = base64.b64decode(m.group(1))
        else:
            png_bytes = await qr_el.screenshot()
    else:
        png_bytes = await qr_el.screenshot()
    # 打印
    print("\n" + "=" * 60, file=sys.stderr)
    print("📱 小红书登录 — 用小红书 App 扫描下方二维码", file=sys.stderr)
    print("=" * 60 + "\n", file=sys.stderr)
    print(render_qr_ascii(png_bytes, width=40), file=sys.stderr)
    print("\n" + "=" * 60, file=sys.stderr)
    print(f"⏳ 等待扫码 (超时 {LOGIN_TIMEOUT_S}s)", file=sys.stderr)
    sys.stderr.flush()
    # 轮询
    waited = 0
    while waited < LOGIN_TIMEOUT_S:
        await asyncio.sleep(2)
        waited += 2
        try:
            if not await main_page.query_selector_all('text="登录"'):
                is_logged_in = True
                return {"status": "ok", "elapsed_s": waited}
        except Exception:
            pass
    return {"status": "timeout", "elapsed_s": waited}


# ==================== MCP Tools ====================
@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="rednote_login",
            description=(
                "登录小红书。\n"
                "- **cookie 模式 (默认)**: 自动从 REDNOTE_COOKIES_FILE 注入, 无需操作\n"
                "- **扫码模式**: 若 cookie 无效, 调用本工具会打印 ASCII 二维码到终端 stderr, 用小红书 App 扫码"
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="rednote_health",
            description="检查服务状态/登录态/cookie 文件。无副作用。",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="rednote_explore",
            description=(
                "抓取小红书首页推荐 feed。无关键词, 适合拿当下热门。"
                "返回 [title, url, author, likes] 列表。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "default": 10},
                },
            },
        ),
        Tool(
            name="rednote_search_notes",
            description=(
                "关键词搜小红书笔记, 返回标题+URL+作者+点赞数。\n"
                "需要登录 (cookie 模式已自动处理)。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "keywords": {"type": "string", "description": "搜索关键词, 如 '京都7日游 自由行'"},
                    "limit": {"type": "integer", "default": 10, "maximum": 30},
                },
                "required": ["keywords"],
            },
        ),
        Tool(
            name="rednote_get_note_content",
            description="根据笔记 URL 获取正文文本(前 5000 字)。",
            inputSchema={
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"],
            },
        ),
        Tool(
            name="rednote_get_note_comments",
            description="抓取笔记评论(最多 50 条)。",
            inputSchema={
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    global is_logged_in
    try:
        if name == "rednote_health":
            cookies_status = "no_file"
            if os.path.exists(COOKIES_FILE):
                try:
                    with open(COOKIES_FILE) as f:
                        ck = json.load(f)
                    cookies_status = f"loaded {len(ck)} cookies"
                except Exception as e:
                    cookies_status = f"error: {e}"
            return [TextContent(type="text", text=json.dumps({
                "status": "ok",
                "logged_in": is_logged_in,
                "cookie_injected": cookie_injected,
                "cookies_file": COOKIES_FILE,
                "cookies_status": cookies_status,
                "browser_data_dir": BROWSER_DATA_DIR,
                "headless": HEADLESS,
            }, ensure_ascii=False, indent=2))]

        # 启动浏览器 (会顺带注入 cookie)
        if name == "rednote_login":
            await ensure_browser()
            if is_logged_in:
                return [TextContent(type="text", text=(
                    f"✅ 已登录 (cookie 模式)\n"
                    f"   cookies: {COOKIES_FILE}\n"
                    f"   失效时: 重新登录小红书 web → 抄 cookie → 更新文件"
                ))]
            # 兜底: 扫码
            r = await trigger_login_qr_scan()
            if r["status"] == "ok":
                return [TextContent(type="text", text=f"✅ 扫码登录成功 (耗时 {r['elapsed_s']}s)")]
            elif r["status"] == "timeout":
                return [TextContent(type="text", text=f"⏰ 扫码超时 ({r.get('elapsed_s')}s)。可能原因: IP 300012 风控 / QR 被截断")]
            return [TextContent(type="text", text=f"❌ 登录失败: {r.get('error')}\n建议: 走 cookie 模式")]

        # 以下需要登录
        await ensure_browser()
        if not is_logged_in:
            return [TextContent(type="text", text="未登录。请先调用 rednote_login (cookie 模式会尝试自动注入)")]

        if name == "rednote_explore":
            limit = int(arguments.get("limit", 10))
            try:
                await main_page.goto(f"{XHS_DOMAIN}/explore", timeout=30000, wait_until="domcontentloaded")
                await asyncio.sleep(5)
            except Exception as e:
                return [TextContent(type="text", text=f"❌ explore 加载失败: {e}")]
            data = await main_page.evaluate("""
                (limit) => {
                    const cards = document.querySelectorAll('section.note-item, a.cover, [data-v-][class*="note"]');
                    const seen = new Set();
                    const items = [];
                    for (const card of cards) {
                        const a = card.tagName === 'A' ? card : card.querySelector('a[href*="/explore/"], a[href*="/search_result/"]');
                        if (!a) continue;
                        const href = a.getAttribute('href');
                        if (!href || seen.has(href)) continue;
                        seen.add(href);
                        const root = card.closest('section') || card;
                        // 找标题: 多个 selector 兜底
                        let title = '';
                        for (const sel of ['.title', '[class*="title"]', 'span', '.footer span']) {
                            const el = root.querySelector(sel);
                            if (el && el.innerText.trim().length > 4) {
                                title = el.innerText.trim().slice(0, 100);
                                break;
                            }
                        }
                        if (!title) {
                            // 兜底: 整个 card 文本
                            const allText = (root.innerText || '').trim();
                            title = allText.split('\\n')[0]?.slice(0, 100) || '(无标题)';
                        }
                        items.push({title, url: href.startsWith('http') ? href : 'https://www.xiaohongshu.com' + href});
                        if (items.length >= limit) break;
                    }
                    return items;
                }
            """, limit)
            if not data:
                return [TextContent(type="text", text="未抓到 explore 笔记(可能 cookie 失效 / 页面结构变化)")]
            txt = f"explore feed ({len(data)} 条):\n\n"
            for i, p in enumerate(data, 1):
                txt += f"{i}. {p['title']}\n   {p['url']}\n\n"
            return [TextContent(type="text", text=txt)]

        if name == "rednote_search_notes":
            keywords = arguments["keywords"]
            limit = int(arguments.get("limit", 10))
            search_url = f"{XHS_DOMAIN}/search_result?keyword={keywords}&source=web_explore_feed"
            try:
                await main_page.goto(search_url, timeout=30000, wait_until="domcontentloaded")
                await asyncio.sleep(6)  # 搜索结果 JS 渲染慢
            except Exception as e:
                return [TextContent(type="text", text=f"❌ 搜索页加载失败: {e}")]
            data = await main_page.evaluate("""
                (limit) => {
                    const cards = document.querySelectorAll('section.note-item, a[href*="/search_result/"]');
                    const seen = new Set();
                    const items = [];
                    for (const card of cards) {
                        const a = card.tagName === 'A' ? card : card.querySelector ? card.querySelector('a[href*="/search_result/"]') : null;
                        if (!a) continue;
                        const href = a.getAttribute('href');
                        if (!href || seen.has(href) || !href.includes('/search_result/')) continue;
                        seen.add(href);
                        const root = card.closest('section') || card;
                        let title = '';
                        for (const sel of ['.title', '[class*="title"]', 'span.title']) {
                            const el = root.querySelector(sel);
                            if (el && el.innerText.trim().length > 4) {
                                title = el.innerText.trim().slice(0, 100);
                                break;
                            }
                        }
                        if (!title) {
                            const allText = (root.innerText || '').trim();
                            title = allText.split('\\n')[0]?.slice(0, 100) || '(无标题)';
                        }
                        items.push({title, url: href.startsWith('http') ? href : 'https://www.xiaohongshu.com' + href});
                        if (items.length >= limit) break;
                    }
                    return items;
                }
            """, limit)
            if not data:
                return [TextContent(type="text", text=(
                    f"未找到与 '{keywords}' 相关的笔记。\n"
                    f"可能 cookie 失效 → 重新登录小红书 web → 更新 {COOKIES_FILE}"
                ))]
            txt = f"搜索 '{keywords}' 返回 {len(data)} 条:\n\n"
            for i, p in enumerate(data, 1):
                txt += f"{i}. {p['title']}\n   {p['url']}\n\n"
            return [TextContent(type="text", text=txt)]

        if name == "rednote_get_note_content":
            url = arguments["url"]
            try:
                await main_page.goto(url, timeout=30000, wait_until="domcontentloaded")
                await asyncio.sleep(5)
            except Exception as e:
                return [TextContent(type="text", text=f"❌ 笔记加载失败: {e}")]
            text = await main_page.evaluate("() => document.body.innerText.slice(0, 5000)")
            return [TextContent(type="text", text=f"--- 笔记 (前 5000 字) ---\n{text}\n--- URL: {url} ---")]

        if name == "rednote_get_note_comments":
            url = arguments["url"]
            try:
                await main_page.goto(url, timeout=30000, wait_until="domcontentloaded")
                await asyncio.sleep(5)
            except Exception as e:
                return [TextContent(type="text", text=f"❌ 笔记加载失败: {e}")]
            text = await main_page.evaluate("""
                () => {
                    const items = document.querySelectorAll('.comment-item, [class*="comment-item"], [class*="CommentItem"]');
                    return Array.from(items).slice(0, 50).map(el => el.innerText.trim()).filter(t => t && t.length > 2).join('\\n---\\n');
                }
            """)
            return [TextContent(type="text", text=f"--- 评论 ---\n{text or '未抓到评论(可能 cookie 失效 / 评论需展开)'}")]

        return [TextContent(type="text", text=f"未知工具: {name}")]
    except Exception as e:
        return [TextContent(type="text", text=f"❌ {name} 失败: {type(e).__name__}: {e}")]


def main() -> None:
    """stdio MCP 入口 — mcp SDK 1.27+ 新签名。"""
    async def _run() -> None:
        async with stdio_server() as (read_stream, write_stream):
            await app.run(read_stream, write_stream, app.create_initialization_options())
    asyncio.run(_run())


if __name__ == "__main__":
    main()
