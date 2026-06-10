#!/usr/bin/env python3
"""Markdown → A4 PDF renderer (playwright + chromium + WQY 中文).

Usage:
    python3 render_pdf.py <input.md> <output.pdf>

Pipeline:
    1. md → HTML (custom markdown parser, 不引第三方)
    2. HTML + CSS → PDF (playwright headless chromium, system WQY fonts)
    3. 视觉验证 (M3 vision via minimax cn anthropic, 不用 vision_analyze 工具)

环境:
    - /opt/data/.venv (PyMuPDF + playwright)
    - /opt/data/.env 有 MINIMAX_CN_API_KEY
    - 系统装 fonts-wqy-microhei + fonts-wqy-zenhei (中文不方块)
"""
import sys, re, html, os
from pathlib import Path

CSS = """
@page { size: A4; margin: 13mm 11mm; }
* { box-sizing: border-box; }
body { font-family: 'WenQuanYi Micro Hei', 'WenQuanYi Zen Hei', sans-serif;
       font-size: 10pt; line-height: 1.55; color: #1a1a1a; margin: 0; }
h1 { font-size: 19pt; color: #0a3d5c; border-bottom: 3px solid #0a3d5c;
     padding-bottom: 5pt; margin: 14pt 0 10pt; page-break-after: avoid; }
h2 { font-size: 13.5pt; color: #0a3d5c; border-left: 4px solid #0a3d5c;
     padding-left: 8pt; margin: 14pt 0 6pt; page-break-after: avoid;
     background: #f0f6f9; padding: 5pt 8pt; }
h3 { font-size: 11.5pt; color: #2d5d7a; margin: 10pt 0 4pt; page-break-after: avoid; }
h4 { font-size: 10.5pt; color: #444; margin: 8pt 0 3pt; }
p { margin: 3pt 0; }
ul, ol { margin: 3pt 0 3pt 16pt; padding: 0; }
li { margin: 1.5pt 0; }
strong { color: #0a3d5c; }
code { background: #f4f4f4; padding: 0 3pt; border-radius: 2pt; font-size: 8.5pt; }
pre.code { background: #1e1e1e; color: #d4d4d4; padding: 6pt;
           border-radius: 3pt; font-size: 8pt; overflow: hidden; }
blockquote { border-left: 3pt solid #6c8c9f; margin: 4pt 0; padding: 2pt 8pt;
            color: #2a2a2a; background: #f0f6f9; }
table { width: 100%; border-collapse: collapse; margin: 5pt 0;
        font-size: 9pt; page-break-inside: avoid; }
th { background: #0a3d5c; color: white; padding: 3.5pt 5pt; text-align: left; font-weight: 600; }
td { padding: 2.5pt 5pt; border-bottom: 1px solid #ddd; vertical-align: top; }
tr.row-ok td { background: #d4edda; color: #0d4a1f; font-weight: 600;
               border-left: 3pt solid #2e7d32; }
tr.row-x td  { background: #fcd5d5; color: #5a0a0a; font-weight: 600;
               border-left: 3pt solid #c00000; }
"""


def md_to_html(md: str) -> str:
    """极简 markdown → HTML: 标题/列表/表格/引用/代码/加粗/斜体/行内 code."""
    lines = md.split('\n')
    out, in_table, in_code, in_list, list_type, in_quote = [], False, False, False, None, False
    
    def fmt(t):
        t = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', t)
        t = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', t)
        t = re.sub(r'`([^`]+)`', r'<code>\1</code>', t)
        return t
    
    for line in lines:
        if line.startswith('```'):
            if in_code:
                out.append('</code></pre>')
                in_code = False
            else:
                out.append('<pre class="code"><code>')
                in_code = True
            continue
        if in_code:
            out.append(html.escape(line))
            continue
        
        if '|' in line and line.strip().startswith('|') and line.strip().endswith('|'):
            cells = [c.strip() for c in line.strip()[1:-1].split('|')]
            if all(re.match(r'^-+$', c) for c in cells):
                out.append('<thead><tr>' + ''.join(f'<th>{html.escape(c)}</th>' for c in cells) + '</tr></thead><tbody>')
                continue
            if not in_table:
                out.append('<table>')
                in_table = True
            row_ok = any('✅' in c for c in cells)
            row_x  = any('❌' in c for c in cells)
            cls = ' class="row-ok"' if row_ok else (' class="row-x"' if row_x else '')
            out.append(f'<tr{cls}>' + ''.join(f'<td>{fmt(html.escape(c))}</td>' for c in cells) + '</tr>')
            continue
        elif in_table:
            out.append('</tbody></table>')
            in_table = False
        
        m = re.match(r'^(#{1,6})\s+(.+)$', line)
        if m:
            if in_list:
                out.append(f'</{list_type}>')
                in_list, list_type = False, None
            if in_quote:
                out.append('</blockquote>')
                in_quote = False
            out.append(f'<h{len(m.group(1))}>{fmt(m.group(2))}</h{len(m.group(1))}>')
            continue
        
        if line.startswith('> '):
            if in_list:
                out.append(f'</{list_type}>')
                in_list, list_type = False, None
            if not in_quote:
                out.append('<blockquote>')
                in_quote = True
            out.append(f'<p>{fmt(line[2:])}</p>')
            continue
        elif in_quote:
            out.append('</blockquote>')
            in_quote = False
        
        m = re.match(r'^(\s*)[-*+]\s+(.+)$', line)
        if m:
            if list_type != 'ul':
                if in_list:
                    out.append(f'</{list_type}>')
                out.append('<ul>')
                in_list, list_type = True, 'ul'
            out.append(f'<li>{fmt(m.group(2))}</li>')
            continue
        m = re.match(r'^(\s*)\d+\.\s+(.+)$', line)
        if m:
            if list_type != 'ol':
                if in_list:
                    out.append(f'</{list_type}>')
                out.append('<ol>')
                in_list, list_type = True, 'ol'
            out.append(f'<li>{fmt(m.group(2))}</li>')
            continue
        elif in_list and line.strip() == '':
            out.append(f'</{list_type}>')
            in_list, list_type = False, None
        
        if line.strip() == '':
            continue
        out.append(f'<p>{fmt(line)}</p>')
    
    if in_list: out.append(f'</{list_type}>')
    if in_table: out.append('</tbody></table>')
    if in_quote: out.append('</blockquote>')
    if in_code: out.append('</code></pre>')
    return '\n'.join(out)


def render(md_path: str, pdf_path: str, verify: bool = True) -> dict:
    """md → PDF, 返回 {'pages': int, 'size_kb': float, 'm3_score': str (optional)}."""
    from playwright.sync_api import sync_playwright
    
    html_path = pdf_path.replace('.pdf', '.html')
    md = Path(md_path).read_text(encoding='utf-8')
    body = md_to_html(md)
    title = re.search(r'^#\s+(.+)$', md, re.M)
    title = title.group(1) if title else 'Report'
    html_doc = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>{html.escape(title)}</title>
<style>{CSS}</style></head>
<body>{body}</body></html>"""
    Path(html_path).write_text(html_doc, encoding='utf-8')
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
        page = browser.new_context().new_page()
        page.goto(f'file://{html_path}', wait_until='networkidle')
        page.evaluate("document.fonts.ready")
        page.pdf(path=pdf_path, format='A4',
                 margin={'top': '12mm', 'right': '10mm', 'bottom': '14mm', 'left': '10mm'},
                 print_background=True, prefer_css_page_size=True)
        browser.close()
    
    info = {'pdf_path': pdf_path, 'html_path': html_path,
            'size_kb': round(os.path.getsize(pdf_path) / 1024, 1)}
    
    # 页数 (PyMuPDF,装在 /opt/data/.venv)
    try:
        import fitz
        doc = fitz.open(pdf_path)
        info['pages'] = len(doc)
        if verify:
            doc[0].get_pixmap(dpi=110).save('/tmp/preview_p1.png')
        doc.close()
    except ImportError:
        info['pages'] = '?'
    
    # 视觉验证
    if verify and 'pages' in info and info['pages'] != '?':
        try:
            import json, urllib.request, base64, ssl
            env = {}
            for line in open('/opt/data/.env'):
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    v = v.strip()
                    if (v.startswith("'") and v.endswith("'")) or (v.startswith('"') and v.endswith('"')):
                        v = v[1:-1]
                    env[k.strip()] = v
            key, base = env['MINIMAX_CN_API_KEY'], env['MINIMAX_CN_BASE_URL']
            img_b64 = base64.b64encode(open('/tmp/preview_p1.png', 'rb').read()).decode()
            body = {"model": "MiniMax-VL-01", "max_tokens": 800,
                    "messages": [{"role": "user", "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": img_b64}},
                        {"type": "text", "text": "请简短回答:1) 中文是否正常无乱码?2) 排版是否清晰?3) ✅/❌ 行色块强度 1-10?4) 整体评分 0-10。"}
                    ]}]}
            req = urllib.request.Request(base + '/v1/messages',
                data=json.dumps(body).encode('utf-8'),
                headers={'Content-Type': 'application/json', 'x-api-key': key,
                         'anthropic-version': '2023-06-01'})
            with urllib.request.urlopen(req, timeout=60, context=ssl.create_default_context()) as resp:
                r = json.loads(resp.read())
                for c in r['content']:
                    if c['type'] == 'text':
                        info['m3_score'] = c['text']
        except Exception as e:
            info['m3_score'] = f'(verify failed: {e})'
    
    return info


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    md, pdf = sys.argv[1], sys.argv[2]
    info = render(md, pdf)
    print(f"✅ PDF: {info['pdf_path']}")
    print(f"   pages: {info['pages']}, size: {info['size_kb']} KB")
    if 'm3_score' in info:
        print(f"\n=== M3 vision 视觉验证 ===\n{info['m3_score']}")
