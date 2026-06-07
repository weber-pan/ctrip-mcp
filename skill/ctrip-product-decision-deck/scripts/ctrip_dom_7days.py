#!/usr/bin/env python3
"""
ctrip_dom_7days.py — 抓完整 7 日行程 DOM (图文行程 tab)
- 用 /opt/data/.venv/bin/python (已装 playwright)
- 关闭弹窗 → 滚到底 → 抓 innerText + HTML + 截图

用法:
  /opt/data/.venv/bin/python scripts/ctrip_dom_7days.py <productId> <cityId>

产物:
  /opt/data/ctrip-data/dom_text_7days_<pid>.txt   (~20 KB · Day 01-07 + 违约条款 + 费用)
  /opt/data/ctrip-data/dom_html_7days_<pid>.html
  /tmp/ctrip_dom_7days.png

关键字段(从 DOM text 解析):
  - "Day\\n01..07" + 主题标 + 早/午/晚餐 + 景点评分 + 酒店
  - "违约条款": 5%/20%/50%/60%/70% 退订阶梯
  - "费用包含": 6 早餐 + 1 午餐 + 7 日用车 + 接送机
  - "自理费用": 巴厘岛旅游税 ¥75/人
  - 景点评分: 赛武 5.0 / 布罗莫 5.0 / 伊真 4.9 / 水神庙 4.6 / 罗威纳 4.0 / 佩妮达 4.2
"""
import sys
from playwright.sync_api import sync_playwright
from pathlib import Path

OUT = Path('/opt/data/ctrip-data')

def main():
    product_id = sys.argv[1] if len(sys.argv) > 1 else '69762187'
    city_id = sys.argv[2] if len(sys.argv) > 2 else '2'
    url = f'https://vacations.ctrip.com/travel/detail/p{product_id}?city={city_id}'

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            viewport={'width': 1440, 'height': 900},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36'
        )
        page = ctx.new_page()
        page.goto(url, wait_until='domcontentloaded', timeout=30000)
        page.wait_for_timeout(8000)

        # 关弹窗
        for _ in range(5):
            page.keyboard.press('Escape')
            page.wait_for_timeout(300)
        for sel in ['[class*="popup"]', '[class*="mask"]', 'button:has-text("关闭")', 'button:has-text("知道了")']:
            try:
                for i in range(page.locator(sel).count()):
                    try:
                        page.locator(sel).first.click(timeout=2000, force=True)
                        page.wait_for_timeout(300)
                    except: pass
            except: pass

        # 找"图文行程" tab
        try:
            tab = page.locator('text=图文行程').first
            if tab.count() > 0:
                tab.scroll_into_view_if_needed()
                tab.click(force=True, timeout=10000)
                page.wait_for_timeout(4000)
                print('  [✓] 图文行程 tab 已点')
            else:
                print('  [!] "图文行程" tab 未找到,直接抓全文')
        except Exception as e:
            print(f'  点击 tab 错: {e},继续抓全文')

        # 滚到底
        for _ in range(15):
            page.mouse.wheel(0, 1000)
            page.wait_for_timeout(500)
        page.evaluate('window.scrollTo(0, 0)')
        page.wait_for_timeout(2000)

        # 抓 DOM
        txt = page.evaluate('document.body.innerText')
        html = page.content()
        page.screenshot(path='/tmp/ctrip_dom_7days.png')
        browser.close()

    # 保存
    (OUT / f'dom_text_7days_{product_id}.txt').write_text(txt)
    (OUT / f'dom_html_7days_{product_id}.html').write_text(html)
    print(f'[+] 抓 {len(txt)} 字符 → {OUT}/dom_text_7days_{product_id}.txt')

    # 摘要
    import re
    days = re.findall(r'Day\s*\n?\s*0[1-7]', txt)
    has = lambda k: '✓' if k in txt else '✗'
    print(f'\n[摘要]')
    print(f'  Day 数: {len(set(days))}/7')
    print(f'  违约条款: {has("违约金")}')
    print(f'  景点: 布罗莫 {has("布罗莫")} · 伊真 {has("伊真")} · 罗威纳 {has("罗威纳") or has("罗维纳")} · 佩妮达 {has("佩妮达") or has("佩尼达")}')
    print(f'  餐食: 含6早餐 {has("6早餐")} · 1午餐 {has("1午餐")}')

if __name__ == '__main__':
    main()
