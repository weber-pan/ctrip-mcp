"""xhs_core.py — 共享给 ctrip-mcp 调用的纯函数(无 MCP 依赖)。

不直接启动浏览器, 复用 rednote_mcp.server 的全局实例。
ctrip-mcp 启动时:
- import 这文件 → 触发 cookie 检查
- 有 cookie → 暴露 xhs_* tool
- 没 cookie → 隐藏
"""
import os
import json
import asyncio


def _parse_cookie_source(raw: str) -> list | None:
    """解析 cookie 来源, 兼容 DevTools 两种复制格式。

    格式 1 (推荐): JSON array — DevTools 右键 Copy as JSON
      [{"name":"a1","value":"xxx","domain":".xiaohongshu.com",...}, ...]

    格式 2 (DevTools 默认 Ctrl+C): Cookie string
      a1=xxx; web_session=yyy; abRequestId=zzz; ...
    """
    if not raw:
        return None
    raw = raw.strip()
    if not raw:
        return None
    # 尝试 1: JSON array [{"name":"a1","value":"xxx"}, ...]
    if raw.startswith("["):
        try:
            cookies = json.loads(raw)
            if isinstance(cookies, list) and len(cookies) >= 5:
                return cookies
        except Exception:
            pass
    # 尝试 2: Cookie string: name=value; name2=value2
    try:
        pairs = raw.split(";")
        cookies = []
        seen_names = set()
        for p in pairs:
            p = p.strip()
            if "=" not in p:
                continue
            name, value = p.split("=", 1)
            name = name.strip()
            value = value.strip()
            if not name or not value:
                continue
            if name in seen_names:
                continue  # 去重
            seen_names.add(name)
            cookies.append({
                "name": name,
                "value": value,
                "domain": ".xiaohongshu.com",
                "path": "/",
            })
        if len(cookies) >= 5:
            return cookies
    except Exception:
        pass
    return None


def _has_cookie_file(path: str) -> bool:
    """快速检查: REDNOTE_COOKIES env 或文件存在 + 合法 cookie + 至少 5 个"""
    # 优先级 1: REDNOTE_COOKIES (env 配, 兼容 JSON array 和 cookie string)
    raw = os.environ.get("REDNOTE_COOKIES", "")
    if raw:
        cookies = _parse_cookie_source(raw)
        if cookies and len(cookies) >= 5:
            return True
    # 优先级 2: REDNOTE_COOKIES_FILE (文件路径, 向后兼容)
    if not path or not os.path.exists(path):
        return False
    try:
        with open(path) as f:
            cookies = json.load(f)
        return isinstance(cookies, list) and len(cookies) >= 5
    except Exception:
        return False


async def xhs_health() -> dict:
    """健康检查 (带 cookie 文件动态状态)"""
    from . import server as _rednote_server
    cookie_mtime = 0.0
    has_valid_cookie = False
    if os.path.exists(_rednote_server.COOKIES_FILE):
        try:
            cookie_mtime = os.path.getmtime(_rednote_server.COOKIES_FILE)
            has_valid_cookie = _has_cookie_file(_rednote_server.COOKIES_FILE)
        except Exception:
            pass
    return {
        "status": "ok",
        "cookie_injected": _rednote_server.cookie_injected,
        "logged_in": _rednote_server.is_logged_in,
        "cookie_source": "REDNOTE_COOKIES" if _rednote_server.COOKIES_RAW else "REDNOTE_COOKIES_FILE",
        "cookies_file": _rednote_server.COOKIES_FILE,
        "cookie_file_exists": os.path.exists(_rednote_server.COOKIES_FILE),
        "cookie_file_has_valid_json": has_valid_cookie,
        "cookie_file_mtime": cookie_mtime,
        "browser_data_dir": _rednote_server.BROWSER_DATA_DIR,
        "mcphub_env_hint": "更新: mcphub 面板改 REDNOTE_COOKIES env → 重启服务 → 新 cookie 生效",
    }


async def xhs_search_notes(keywords: str, limit: int = 10) -> dict:
    """关键词搜小红书"""
    from . import server as _rednote_server
    await _rednote_server.ensure_browser()
    if not _rednote_server.is_logged_in:
        return {"status": "no_login", "hint": f"cookie 失效, 更新 {_rednote_server.COOKIES_FILE}"}
    search_url = f"{_rednote_server.XHS_DOMAIN}/search_result?keyword={keywords}&source=web_explore_feed"
    try:
        await _rednote_server.main_page.goto(search_url, timeout=30000, wait_until="domcontentloaded")
        await asyncio.sleep(6)
    except Exception as e:
        return {"status": "error", "error": f"搜索页加载失败: {e}"}
    data = await _rednote_server.main_page.evaluate("""
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
        return {"status": "empty", "keywords": keywords, "items": [],
                "hint": "可能 cookie 失效, 重新登录小红书 web → 更新 cookie 文件"}
    return {"status": "ok", "keywords": keywords, "count": len(data), "items": data}


async def xhs_explore(limit: int = 10) -> dict:
    """首页推荐 feed"""
    from . import server as _rednote_server
    await _rednote_server.ensure_browser()
    if not _rednote_server.is_logged_in:
        return {"status": "no_login", "items": []}
    try:
        await _rednote_server.main_page.goto(f"{_rednote_server.XHS_DOMAIN}/explore", timeout=30000, wait_until="domcontentloaded")
        await asyncio.sleep(5)
    except Exception as e:
        return {"status": "error", "error": f"explore 加载失败: {e}"}
    data = await _rednote_server.main_page.evaluate("""
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
                let title = '';
                for (const sel of ['.title', '[class*="title"]', 'span', '.footer span']) {
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
    return {"status": "ok", "count": len(data), "items": data}


async def xhs_get_note_content(url: str, max_chars: int = 5000) -> dict:
    """拿笔记正文"""
    from . import server as _rednote_server
    await _rednote_server.ensure_browser()
    if not _rednote_server.is_logged_in:
        return {"status": "no_login"}
    try:
        await _rednote_server.main_page.goto(url, timeout=30000, wait_until="domcontentloaded")
        await asyncio.sleep(5)
    except Exception as e:
        return {"status": "error", "error": f"笔记加载失败: {e}"}
    text = await _rednote_server.main_page.evaluate(f"() => document.body.innerText.slice(0, {max_chars})")
    return {"status": "ok", "url": url, "content": text}
