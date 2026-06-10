---
name: markdown-report-pdf
description: |
  **智能 PDF 报告向导** (2026-06-10 V5.1 抽象)。用户说"**出旅游报告**"/"**体检行程**"/"**选哪个团**"/"**排行程**"时, skill = 向导 (3 套模板智能推荐 + 三档追问 + 1 页预览), 用户 = 填料 (提供文件/字段), Agent = 渲染 (走 pipeline)。
  3 套模板: A. 出行全包报告(12 章, V5 风格) / B. 多产品对比(9 章) / C. 自由规划(10 章)。
  渲染 pipeline: 走 playwright + chromium + WQY 中文系统字体 + 自定义 CSS + M3 vision 视觉验证。
  触发: "出 PDF" / "出旅游报告" / "把报告转 PDF" / "打印成 PDF" / "报告给领导看" / "出发前必读" / "出行全包" / "体检行程" / "选哪个团" / "多产品对比" / "帮我排行程" / "走 V5 模板" / "report to PDF" / "渲染 PDF"。
  ⚠️ 不用 pandoc/weasyprint(都不装)也不用 mmx image(没有 PDF 端点)。
  ⚠️ 不要用 vision_analyze 工具(已知 404),用 m3-native-vision 的 m3_vision.vision() 验渲染。
  ⚠️ md_to_html 必须对每个 <td> cell 单独过 fmt() 处理 **bold**, 否则 PDF 表格里 200+ 星号残留 (Pitfall 7)。
  ⚠️ 流程/SOP 内容**绝不用代码块** (黑底灰字几乎不可读), 必须用 3 列表格 (模式 B, M3 评 9.5/10)。
---

# Markdown → PDF (playwright + chromium)

A4 印刷级 PDF。中文用 WQY 字体(系统装好)。3 步走完:HTML → PDF → 视觉验证。

## 1. 完整 pipeline(3 步)

### Step 1: markdown → HTML(自定义 markdown_to_html)

```python
import re, html

def md_to_html(md):
    lines = md.split('\n')
    out = []
    in_table = in_code = in_list = in_quote = False
    list_type = None
    
    def fmt(t):
        t = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', t)
        t = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', t)
        t = re.sub(r'`([^`]+)`', r'<code>\1</code>', t)
        return t
    
    for line in lines:
        if line.startswith('```'):
            if in_code: out.append('</code></pre>'); in_code = False
            else: out.append('<pre class="code"><code>'); in_code = True
            continue
        if in_code: out.append(html.escape(line)); continue
        
        # table (✅/❌ 行加 row-ok / row-x 类)
        if '|' in line and line.strip().startswith('|') and line.strip().endswith('|'):
            cells = [c.strip() for c in line.strip()[1:-1].split('|')]
            if all(re.match(r'^-+$', c) for c in cells):
                out.append('<thead><tr>' + ''.join(f'<th>{html.escape(c)}</th>' for c in cells) + '</tr></thead><tbody>'); continue
            if not in_table: out.append('<table>'); in_table = True
            row_has_ok = any('✅' in c for c in cells)
            row_has_x  = any('❌' in c for c in cells)
            cls = ' class="row-ok"' if row_has_ok else (' class="row-x"' if row_has_x else '')
            out.append(f'<tr{cls}>' + ''.join(f'<td>{fmt(html.escape(c))}</td>' for c in cells) + '</tr>')
            continue
        elif in_table: out.append('</tbody></table>'); in_table = False
        
        m = re.match(r'^(#{1,6})\s+(.+)$', line)
        if m:
            if in_list: out.append(f'</{list_type}>'); in_list = False; list_type = None
            if in_quote: out.append('</blockquote>'); in_quote = False
            out.append(f'<h{len(m.group(1))}>{fmt(m.group(2))}</h{len(m.group(1))}>')
            continue
        
        if line.startswith('> '):
            if in_list: out.append(f'</{list_type}>'); in_list = False; list_type = None
            if not in_quote: out.append('<blockquote>'); in_quote = True
            out.append(f'<p>{fmt(line[2:])}</p>')
            continue
        elif in_quote: out.append('</blockquote>'); in_quote = False
        
        m = re.match(r'^(\s*)[-*+]\s+(.+)$', line)
        if m:
            if list_type != 'ul':
                if in_list: out.append(f'</{list_type}>')
                out.append('<ul>'); in_list = True; list_type = 'ul'
            out.append(f'<li>{fmt(m.group(2))}</li>')
            continue
        m = re.match(r'^(\s*)\d+\.\s+(.+)$', line)
        if m:
            if list_type != 'ol':
                if in_list: out.append(f'</{list_type}>')
                out.append('<ol>'); in_list = True; list_type = 'ol'
            out.append(f'<li>{fmt(m.group(2))}</li>')
            continue
        elif in_list and line.strip() == '':
            out.append(f'</{list_type}>'); in_list = False; list_type = None
        
        if line.strip() == '': continue
        out.append(f'<p>{fmt(line)}</p>')
    
    if in_list: out.append(f'</{list_type}>')
    if in_table: out.append('</tbody></table>')
    if in_quote: out.append('</blockquote>')
    if in_code: out.append('</code></pre>')
    return '\n'.join(out)
```

### Step 2: HTML + CSS → PDF (playwright)

```python
from playwright.sync_api import sync_playwright

# A4 + 中文友好 CSS (WQY 系统字体)
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

def render_pdf(md_path, html_path, pdf_path):
    md = open(md_path, encoding='utf-8').read()
    body = md_to_html(md)
    html_doc = f"""<!DOCTYPE html><html lang="zh-CN"><head>
<meta charset="utf-8"><title>Report</title><style>{CSS}</style></head>
<body>{body}</body></html>"""
    open(html_path, 'w', encoding='utf-8').write(html_doc)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
        page = browser.new_context().new_page()
        page.goto(f'file://{html_path}', wait_until='networkidle')
        page.evaluate("document.fonts.ready")
        page.pdf(path=pdf_path, format='A4',
                 margin={'top': '12mm', 'right': '10mm', 'bottom': '14mm', 'left': '10mm'},
                 print_background=True, prefer_css_page_size=True)
        browser.close()
    return pdf_path
```

### Step 3: 视觉验证(M3 vision, 不要 vision_analyze 工具)

```python
# 1. PDF 转 PNG (PyMuPDF,装在 /opt/data/.venv)
import fitz
doc = fitz.open(pdf_path)
print(f"页数: {len(doc)}")
doc[0].get_pixmap(dpi=110).save('/tmp/preview_p1.png')

# 2. M3 vision 验中文 + 排版(不要 vision_analyze 工具,会 404!)
import os, json, urllib.request, base64, ssl
env = {}
for line in open('/opt/data/.env'):
    line = line.strip()
    if line and not line.startswith('#') and '=' in line:
        k, v = line.split('=', 1)
        v = v.strip()
        if (v.startswith("'") and v.endswith("'")) or (v.startswith('"') and v.endswith('"')):
            v = v[1:-1]
        env[k.strip()] = v
key = env['MINIMAX_CN_API_KEY']
base = env['MINIMAX_CN_BASE_URL']

img_b64 = base64.b64encode(open('/tmp/preview_p1.png', 'rb').read()).decode()
body = {"model": "MiniMax-VL-01", "max_tokens": 800,
        "messages": [{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": img_b64}},
            {"type": "text", "text": "请简短回答:1) 中文是否正常无乱码?2) 排版是否清晰?3) ✅/❌ 行色块强度(1-10)?4) 整体评分 0-10。"}
        ]}]}
req = urllib.request.Request(base + '/v1/messages',
    data=json.dumps(body).encode('utf-8'),
    headers={'Content-Type': 'application/json', 'x-api-key': key,
             'anthropic-version': '2023-06-01'})
with urllib.request.urlopen(req, timeout=60, context=ssl.create_default_context()) as resp:
    r = json.loads(resp.read())
    for c in r['content']:
        if c['type'] == 'text': print(c['text'])
```

## 2. 调色经验(2026-06-07 实战 5 轮)

| 轮 | 改动 | M3 评分 | 经验 |
|---|---|---|---|
| 1 | 基础(白底) | 7.5/10 | 起步线 |
| 2 | 加 row-ok/row-x 浅底色 | 6.5/10 | 浅色对比弱,**反而降分** |
| 3 | row-ok/x 加粗 + 加深 | 7.5/10 | 加粗修复 |
| 4 | row-ok/x 加 3pt 左色条 + 加深 | 7.5/10 | 视觉锚点 |
| 5 | h2 加浅蓝底 block | — | 章节区分 |

**经验**:
- 第 1 次色要**深**:`#c00000`(深红)+ `#2e7d32`(深绿) + 3pt 左侧色条 = 醒目
- 浅色底 (#f0faf4) 永远不够,**至少** `#d4edda` 起
- 表格 `border-left: 3pt solid` 是**色条之王**,比加色块更省空间
- 别在第 1 轮就调到位,**先问 M3 评分,再**迭代,不要盲调

## 3. 已知坑(2026-06-07 填)

### 1. 工具选择: pandoc/weasyprint/chrome 全无
`which pandoc weasyprint wkhtmltopdf google-chrome chromium` 都 NOT FOUND
**解法**: 走 playwright 自带 chromium(`/opt/data/home/.cache/ms-playwright/chromium-1223/chrome-linux64/chrome`)

### 2. vision_analyze 工具 404,绕开
**症状**: `vision_analyze(image=...)` 返 "404 nginx"
**原因**: hermes 网关路由坏
**解法**: 用 m3-native-vision 的 m3_vision.vision() 1 行调用,**不要** vision_analyze 工具

### 2.1 ⭐ m3_vision Python 包未装时用 m3_vision.js fallback (2026-06-09 {{目的地}}行程报告踩)
**症状**: `from m3_vision import vision` → `ModuleNotFoundError`。`find / -name "m3_vision*"` 只有 `/tmp/m3_vision_test.py` 和 `/opt/data/ctrip-mcp/skill/ctrip-product-decision-deck/scripts/m3_vision.js`。
**根因**: `m3_vision` Python 包未安装(只在 ctrip-mcp 仓库作为 Node 脚本存在,不是 pip 包)。
**修法**: 直接调用现成的 Node 脚本,绕过 Python 包:
```bash
node /opt/data/ctrip-mcp/skill/ctrip-product-decision-deck/scripts/m3_vision.js \
  /tmp/preview_p1.png \
  "请简短回答:1) 中文是否正常无乱码?2) 排版是否清晰?3) 表格是否整齐?4) ✅❌行色块对比度(1-10)?5) 整体评分 0-10。6) 给出 3 条改进建议。"
```
脚本自动从 `/opt/data/.env` 读 `MINIMAX_CN_API_KEY`,调 m3 API(anthropic 兼容),输出 JSON-decoded 文本。**比 vision_analyze 工具稳定 100 倍**(无网关路由层)。

**使用场景**:
- 任何需要 M3 vision 验渲染(报告 PDF / PPT HTML / 任何生成图片)
- 比 `mcp_mcphub_smart_*` 调用 m3 也更稳(同样绕开聚合器)

**输出格式**: 1-6 数字 + 短文本,直接 grep 解析进报告("M3 vision 评分 8/10")。

### 3. PyMuPDF 装在 /opt/data/.venv,不是 execute_code 沙盒
execute_code 沙盒默认用 `/opt/hermes/.venv`,没 PyMuPDF
**解法**: `/opt/data/.venv/bin/pip install -q PyMuPDF` 然后用 `/opt/data/.venv/bin/python` 跑

### 4. 中文字体
**装好**: `fc-list :lang=zh` 应该有 WenQuanYi Micro Hei + Zen Hei
**没装**: `apt install fonts-wqy-microhei fonts-wqy-zenhei`
不装的话 PDF 中文 = 方块

### 5. page.evaluate("document.fonts.ready") 必加
不加 → 字体还没加载就开始 render → 中文偶发方块
加 → 等所有 webfont 加载完才 render → 中文稳

### 7. md_to_html 必须处理 `<td>` 内的 `**bold**`, 不能漏 (2026-06-09 V4 PDF 踩)
**症状**: PDF 表格里 `**7.4 周六**` `**21:30**` `**{{目的地}} {{目的机场}} D 抵达**` 字面星号显示, **加粗失败** (V4 首页 208 个 `**` 残留, M3 vision 评 4.5/10)
**根因**: 简易 md→html 函数只在 `<p>` 段里跑 `re.sub(r"\*\*(.+?)\*\*", ...)` , **没在 `<td>` 单元格里跑**
**修法** (本 skill 现有 `fmt()` 函数已经覆盖 — 关键模式):
```python
def fmt(t):  # 必须对每个 cell 单独跑
    t = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', t)
    t = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', t)
    t = re.sub(r'`([^`]+)`', r'<code>\1</code>', t)
    return t

# ⭐ 表格行处理: 每个 cell 单独过 fmt, 不能只在 row 模板里写一次
out.append(f'<tr{cls}>' + ''.join(f'<td>{fmt(html.escape(c))}</td>' for c in cells) + '</tr>')
#                                                                  ^^^^^^^^ 必须 fmt(c)
```

**复现命令** (V4 验证):
```bash
grep -c "<strong>" report.html  # 应 >= 50 (V4 实测 116, 修复后)
grep -c "\\\\*\\\\*" report.html       # 应 == 0 (V4 修后, 修复前 208)
```

**M3 vision 必查** (M3 会主动指出残留星号):
> "通篇检查未发现任何裸露的 `**` 加粗标记" → 7.5/10 升到 8.5/10

### 7.1 ⭐ 表格分隔行 `|---|---|` 错渲染为 `<th>---</th>` 修法 (2026-06-10 V5 PDF 踩)
**症状**: M3 vision 报"表头第一行显示 `---/---/---` 占位符" (V5 P7 截图, 整体评分 6/10)
**根因**: 老版 `md_to_html` 把 markdown 表格分隔行当 `<th>` 渲染, 输出 `---` 文字
**修法** (V5 实测 0 残留):
```python
table_header_emitted = False
for line in lines:
    if '|' in line and line.strip().startswith('|'):
        cells = [c.strip() for c in line.strip()[1:-1].split('|')]
        # ⭐ 分隔行(---|---|)直接 skip, 不输出 --- 文字
        if all(re.match(r'^-+:?$', c) for c in cells):
            if not table_header_emitted:
                out.append('</thead><tbody>')  # 闭合 thead, 开启 tbody
                table_header_emitted = True
            continue
        if not in_table:
            out.append('<table><thead>'); in_table = True; table_header_emitted = False
        if not table_header_emitted:
            out.append('<tr>' + ''.join(f'<th>{fmt(html.escape(c))}</th>' for c in cells) + '</tr>')
            table_header_emitted = "pending_separator"  # 等下个分隔行闭合
        else:
            # ... 普通行处理
```
**复现命令** (V5 验证):
```bash
grep -c "<th>---</th>" report.html   # 应 == 0 (V5 修后)
grep -c "<th>.*<th>" report.html      # 多个表头, 只看是否有 <th>--- 残留
```

### 7.2 ⭐ `{.newpage}` 强制分页 + class 属性 bug (2026-06-10 V5 PDF 踩)
**症状**: 章节标题里写 `## §九、出发前必读 {.newpage}` 期望分新页, 但 HTML 输出 `<h2 newpage>` 而不是 `<h2 class="newpage">`, CSS 不生效
**根因**: f-string 拼 class 时漏了 `class="..."` 包裹
**修法** (V5 实测 2 个 newpage 都生效):
```python
# 标题 regex 支持 {.class} 后缀
m = re.match(r'^(#{1,6})\s+(.+?)(\s+\{\.([\w-]+)\})?\s*$', line)
# ⚠ 关键: f-string 要带 class="..." 引号
extra_class = f' class="{m.group(4)}"' if m.group(4) else ''
out.append(f'<h{len(m.group(1))}{extra_class}>{fmt(m.group(2))}</h{len(m.group(1))}>')
```
**CSS** (V5):
```css
h2.newpage { page-break-before: always; }
```
**用法** (markdown 源):
```markdown
## 九、出发前必读 9 条 {.newpage}  ← 长章节强制起新页
## 十二、数据来源与版本 {.newpage}  ← 末章独立
```

### 7.3 ⭐ 章节分页原则 (2026-06-10 V5 PDF 教训)
**M3 vision 报"V5 P7 缺第 1 点"**: 因为 §九 第 1 点流程被分页切断在 P6 末尾, P7 直接从第 2 点开始
**原则**:
- **长章节** (含 5+ 段) → 强制 `{.newpage}` 起新页, 避免内容被截
- **短章节** (1-2 段) → 跟前后文自然分页即可
- **附录/末章** → 永远 `{.newpage}` 独立一页
- M3 vision 看到"列表 1 缺失/2-3 悬空" = 大概率分页问题, **优先检查**

### 7.4 ⭐ 代码块黑底灰字问题 — 改用表格渲染流程/清单 (2026-06-10 V5.1 PDF 踩)
**症状**: M3 vision 报"§11.2 §11.3 取消 SOP 显示灰字黑底, 几乎看不见, 整体评分 3.5/10" (V5 第一次跑)
**根因**: 
- 简易 `pre.code` CSS 用 `background: #1e1e1e; color: #d4d4d4` 灰字 + 黑底
- 流程/清单类内容用 ` ``` ``` ` 围栏 + `↓` 箭头占位, 渲染时灰箭头字在黑底上对比度极低
- 中文 8pt 灰字 + 黑底 + 多空行 = 几乎不可读

**修法** (V5.1 验证, 整体评分回升到 9.5/10):
- **流程/SOP/清单类内容** → **改成 markdown 表格**(`| 步骤 | 时间窗 | 行动 |`)
- 表格渲染:深蓝表头 `#0a3d5c` + 白字 + 白色 td, 对比度 10/10
- 优势:可勾选、可复制、彩色高亮、视觉层次清晰
- 保留 `pre.code` 用途:真正**多行代码** (Python/SQL/JSON), 不要用于流程图

**实战位置** (V5.1 §11.2/11.3):
```python
# ❌ 错: 代码块 + ↓ 箭头
```
```
鹰航短信/邮件通知取消
        ↓
立即打鹰航中国客服 4008-789-789
        ↓
要求改签到: ① {{去程直飞航班}} ...
```

```python
# ✅ 对: 表格三列
```
| 步骤 | 时间窗 | 行动 |
|---|---|---|
| ① 收到通知 | 7.4 起飞前 24h | 鹰航短信/邮件通知取消 |
| ② 第一电话 | 通知后 30min 内 | 鹰航客服 **4008-789-789** |
| ③ 要求改签 | 通话 1 | 优先:① **{{去程直飞航班}} 吉祥 09:30 直飞** |
```

**M3 vision 必查** (M3 会主动指出"代码块对比度极低"):
> "代码块应该是白字黑底(终端风格), 但实际渲染成浅灰字 + 黑底 = 几乎看不见" → 整体 8.5/10 降到 3.5/10
> "**改表格后**: 6 步骤流程完整, 关键信息用蓝色加粗, 视觉重点突出" → 8/10 升到 9.5/10

### 7.6 ⭐ 框架 ≠ 内容 — skill 模板零硬编码铁律 (2026-06-10 V5.1 抽象, 用户原话)

**用户原话**: "只是这个框架, 里面内容不能一样。你要怎么做。"

**铁律**:
- skill 的 `templates/*.md` 模板文件 **只允许** 含 `{{占位符}}` / 字段结构 / 通用字段名
- **禁止** 任何具体内容: 真实地名 / 航班号 / 酒店名 / 餐厅名 / 订单号 / 电话 / 货币 / 行程日期 / 评分
- 实战案例 (如 V5.1 {{目的地}}) 放 `references/<topic>.md` 单独管理, 模板里**只引用不展开**
- 写完模板必跑 `scripts/verify-no-hardcoded.py` 自验 (黑名单 80+ V5.1 字眼, 含中英{{目的地}}字段)

**为什么这是铁律**:
1. skill = 类级文档, 适用未来 N 个场景; 一旦硬编码 V5.1 {{目的地}}, 跑东京/巴黎/马代就成了"找{{目的地}}数据"的怪胎
2. 实战案例脱离后, 模板的可读性反而↑ (没有上下文噪声, 一眼看到字段结构)
3. git diff 跨场景时 0 变更, 只换用户现场填的内容

**V5.1 真实翻车** (写模板时的 6 处硬编码):

| # | 文件 | 违规内容 | 修法 |
|---|---|---|---|
| 1 | `patterns/d-day-checklist.md` | "实战案例 (V5.1 {{目的地}}): 见..." | 改 "实战案例: 见..." |
| 2 | `patterns/sop-6step.md` | "(V5.1 {{目的地}}去程+返程 SOP)" | 删 |
| 3 | `patterns/delay-tier.md` | "(V5.1 {{目的地}}机场延误)" | 删 |
| 4 | `patterns/day-by-day.md` | "(V5.1 {{目的地}} D1-D7)" | 删 |
| 5 | `patterns/pros-cons.md` | "(V4 {{目的地}} 6+6)" + "M3 vision 反馈 (V5.1 {{目的地}})" | 改通用, 加 "## M3 vision 反馈 (实战)" |
| 6 | `trip-all-in-one.md` | "({{目的地}}那种)" | 删 |
| + | 6 处全部抽出到 `references/v5-case-study.md` 案例 1-5 |

**自验命令** (必走, 写完模板立刻跑):
```bash
/opt/data/.venv/bin/python /opt/data/skills/markdown-report-pdf/scripts/verify-no-hardcoded.py
```
**期望输出**: "🎉 全部干净, 框架与内容彻底分离, 退出码 0"

**经验**: 即使模板看起来"通用", 一旦想加"实战案例"段, **立即** 抽 references/, 别往模板里塞。**经验规律**: 模板里"实战案例"段出现 5 次 = 100% 会被审稿人抓出。

**跨场景迁移** (V5.1 实战):
未来跑"东京 8.1-8.7" / "巴黎 9.10-9.20" / "马代 10.1-10.7", 套同套模板, 字段替换即可:
| 字段 | 替换 | 例子 |
|---|---|---|
| `{{目的地}}` | 城市 | "东京" |
| `{{航班号}}` | 实际 | "NH 920" 替换 "{{去程航班 1}}" |
| `{{酒店名}}` | 实际 | "新宿王子大饭店" 替换 "{{酒店名 A}}" |
| `{{餐厅名}}` | 实际 | "一兰拉姆面" 替换 "{{24h 餐厅}}" |
| `{{航司客服}}` | 实际 | 全日空 03-6735-1000 替换 鹰航 4008-789-789 |
| `{{货币}}` | 实际 | 日元 1:20 替换 印尼盾 1:2000 |

5 套设计模式本身**不变**, 字段替换即可。

### 7.5 ⭐ D-Day 倒计时是 checklist 的灵魂 (2026-06-10 V5.1 PDF 实战)
**场景**: 用户说"细化 7 件必做" → 加 D-Day 倒计时
**触发**:
- 用户提"必做"/"清单"/"任务"/"待办"/"行动项" → 自动加 D-Day 列
- 起飞日期已知 → 算 D-N = (起飞日 - 今天).days

**模板** (V5.1 实战, 7-8 行最舒服):
```markdown
| # | 必做事 | 截止 | D-Day |
|---|---|---|---|
| 1 | **买吉祥 {{去程直飞航班}}/{{返程直飞航班}} 兜底票** {{兜底票预算}} | **6.30** | D-30 |
| 2 | **自办 eVOA** {{签证官网}}, {{签证费}}/人 | **7.1** | D-29 |
| 3 | **买{{保险公司}}保险** ¥200/人, {{保险预算}}(2 人 7 天) | **7.1** | D-29 |
| 4 | 问客服 D1 南部酒店 24h 前台 | **6.20** | D-14 |
| 5 | 问客服 D6 {{区域 4}}停航改线规则 | **6.20** | D-14 |
| 6 | 鹰航 App 绑 PNR + 航班状态订阅 | **6.30** | D-4 |
| 7 | 换 ¥2000 人民币等值印尼盾 | **7.3** | D-1 |
| 8 | 打印应急通讯录 + 兜底票 PDF 各 2 份 | **7.3** | D-1 |
```

**M3 评分** (V5.1 P2): **9/10**
> "8 条任务**全部 actionable**, 无废话 / D-Day 倒计时排序**制造了紧迫感** / 关键参数(PNR、URL、航班号、金额)**全部内联**"

### 8. PyMuPDF (fitz) 装在 /opt/data/.venv, 不在 execute_code 沙盒 (2026-06-09 实战)
**症状**: `execute_code` 里 `import fitz` → `ModuleNotFoundError`
**根因**: `execute_code` 默认 venv = `/opt/hermes/.venv`, 没 PyMuPDF
**解法**: 用 `/opt/data/.venv/bin/python3 -c "import fitz; ..."` 走 venv python

**fitz 1.27+ PDF 转 PNG** (验证 PDF 渲染用):
```python
import fitz
doc = fitz.open(pdf_path)
for i, page in enumerate(doc):
    pix = page.get_pixmap(dpi=120)
    pix.save(f"page_{i+1:02d}.png")  # 120 DPI 适合 M3 vision
```

### 6. 「下载服务器异常」是 WebUI 前端 PDF.js 预览链失败,不是 server 错 (2026-06-07)

**根因**(`/opt/data/hermes-webui/static/ui.js:8108-8143`):
1. `fetch('api/media?path=...')` 拿 PDF
2. `pdfjsLib.getDocument({data:buf})` 解析
3. `page.render({canvasContext, viewport})` 渲到 canvas
4. **任何一步错 → catch → fallback `<a download>` + 中文 `pdf_error` = "下载服务器异常"**

**重点**: 服务端 `GET /api/media` **完全健康**(200 / 1.2MB / `Content-Disposition: attachment`),错的是 PDF.js 渲染链(c...[truncated]

## 4. 完整脚本(可直接复制)

见 `scripts/render_pdf.py`(本次实战抽出来的 production-ready 版本)。

## 4.1 交付/下载踩坑(2026-06-07 实战)

**核心结论**: "下载服务器异常" ≠ server 错。这是 WebUI 前端 PDF.js 渲染链(cdn.jsdelivr.net 15s 超时 / CMap / CJK 字体)失败,服务端 `/api/media` 完全健康。详细分发踩坑 + 端口混淆(9119 ≠ 8787) + 三种 100% 能下载的方法 + M3 vision 验渲染,见 `references/distribution-pitfalls.md`。

## 5. 与 web-ppt-studio / ppt-master 区别

| Skill | 输出 | 适用 |
|---|---|---|
| `web-ppt-studio` | 单 HTML 翻页 PPT (横屏) | 演示用,屏幕投影 |
| `ppt-master` | SVG PPT (多张) | 设计精美型 |
| **`markdown-report-pdf`** | A4 PDF (竖屏) | **报告/纪要/分析打印** ← 本 skill |

**触发词不重叠**: 本 skill = "出 PDF" / "打印" / "给领导看"; web-ppt = "翻页 PPT" / "演示"; ppt-master = "SVG 多页"

## 5.1 Skill 位置与同步约定 (2026-06-10 用户拍板)

**用户原话**: "你是放到 ctrip-mcp 项目里吗" / "ctrip 是不是有 skill 脚本啊" / "A" (选 A 方案)

**双位置规则** (本 skill 适用):
1. **通用池** (主): `/opt/data/skills/markdown-report-pdf/`
   - Hermes 通用 skills 池, 所有项目可访问
   - 跟 `ctrip-itinerary-review` / `ctrip-itinerary-review` 等通用 skill 并列
2. **项目内** (副本): `/opt/data/ctrip-mcp/skill/markdown-report-pdf/`
   - ctrip-mcp 项目仓库自包含, `git clone` 拿到
   - 跟 `ctrip-product-report` / `ctrip-product-decision-deck` 等项目内 skill 并列

**为什么双位置**:
- 通用池 = 跨项目复用 (任何"出报告"任务都能用, 不依赖 ctrip-mcp)
- 项目内 = 项目自包含 (clone ctrip-mcp 就能用, 不用先装通用池)
- 不用软链: 项目仓库不能有指向外部的软链, git 追踪不到, clone 出去就断

**同步命令** (每次改完两处都跑):
```bash
cp -r /opt/data/skills/markdown-report-pdf/* /opt/data/ctrip-mcp/skill/markdown-report-pdf/
```

**未来扩展规则**:
- 通用 skill (pipeline / 通用助手) → 放 `/opt/data/skills/<name>/` + 同步到项目
- 项目专属 skill (带项目前缀, 如 `ctrip-*` / `dress-today` / `bazi-fate`) → 放项目内 `skill/<name>/`
- 边界判定: skill 描述里如果含项目专有术语 (ctrip/{{目的地}}/dress-today/bazi), 必放项目内
- 用户问"你放哪了"时, 必答: "通用池 + 项目内副本, X + Y"

**经验教训** (V5.1 抽象时):
- 用户**会反复确认** skill 位置, 这是因为 skill 系统有多层目录 (通用池 / 项目内 / softlink 软链), 透明度不够
- 一次说清双位置 + 同步规则, 比反复答"放 X 还是 Y"省 5+ turns
- 如果不确定放哪, 优先**双位置** (用户验证后可能会简化)

## 8. 智能报告向导 (2026-06-10 V5.1 抽象)

> 用户说"**出旅游报告**"/"**体检行程**"/"**选哪个团**"/"**排行程**"时, 走本节。
> **核心思想**: skill = 向导 (推荐模板 + 追问 + 预览), 用户 = 填料 (提供文件/字段), Agent = 渲染 (走 pipeline)。
> **绝不硬编码内容** (用户原话: "只是这个框架, 里面内容不能一样"): skill 只提供骨架/模式/原则, 具体内容由每次任务现场填。
> **实战案例分离**: 任何具体案例 (如 V5.1 {{目的地}}) 放 `references/v5-case-study.md` 单独管理, 模板文件里**只引用不展开**。
> **自验必走**: 写完模板后, 必须跑 `scripts/verify-no-hardcoded.py` 检查 0 硬编码 (V5.1 自验抓出 6 处违规, 都是模板里写了"实战案例"段)。

### 8.1 三套模板智能推荐 (用户场景 → 模板映射)

用户只要说"出旅游报告", Agent **自动问 1-2 个问题**识别类型, 然后**推荐 3 套**让用户选:

| 类型 | 触发关键词 | 模板 | 适用场景 | 章节数 |
|---|---|---|---|---|
| **A. 出行全包报告** | "出发前必读" / "行程体检" / "出行全包" / "找问题" | `trip-all-in-one` | 已有行程 + 体检/防坑/补漏 ({{目的地}}那种) | 12 章 |
| **B. 多产品对比报告** | "选哪个团" / "选型" / "对比" / "推荐一个" | `multi-compare` | N 个产品/团/方案里挑一个 | 9 章 |
| **C. 自由规划报告** | "排行程" / "自由行" / "帮我规划" / "去哪好" | `plan-from-scratch` | 从 0 设计 (无现成行程) | 10 章 |

**Agent 自动问的 1-2 个关键问题** (挑类型用):
- "您是**已经有行程要体检**, 还是**从 0 排行程**?" → A vs C
- "您是在**几个产品/团里挑一个**, 还是**体检一个已选的**?" → B vs A

**触发"走 V5 模板"**: 用户原话含 "走 V5" / "出行全包" / "V5 风格" → **直接套 A 模板**, 不再问。

### 8.2 三档追问 (必填 / 选填 / 自动补)

**用户选了模板后**, Agent 按下表追问 — **按重要性倒序问, 用户卡哪条停哪条**:

#### 必填 (3 步跑通, 缺一不可)

| # | 字段 | 例子 | 备注 |
|---|---|---|---|
| 1 | **目的地 + 出行日期 + 人数** | "{{目的地}} 7.4-7.10 2 人" | 一句话说完 |
| 2 | **总预算范围** | "¥20000-25000/人" 或 "不限" | 决定推荐档次 |
| 3 | **已有资源清单** | "已订机票/已订酒店/已办签证" | 决定哪些章节要写 |

#### 选填 (越全报告越准, 用户挑着给)

| 字段 | 用途 | 来源 |
|---|---|---|
| 📄 行程单/订单 PDF | 验证真实价位/时刻 | 携程/卖家/航司 |
| 📄 报价单/确认函 | 验证价格口径 | 卖家/旅行社 |
| 📷 护照首页 | 签证章节 | 用户 |
| 🗣 特别要求 | 蜜月/带娃/老人/无障碍 | 用户 |
| 🏨 酒店偏好 | 价位/星级/位置 | 用户 |

#### 自动补 (Agent 智能补全, 用户不用管)

| 内容 | 来源 | 适用 |
|---|---|---|
| 🌤 7 天天气 | `amap-mcp` + `wendao` | 自由行必含 |
| 🍽 7 天餐厅 | `SearchAPI MCP` Google Maps 5 区域 | 自由行必含 |
| 🏨 备选酒店 | `AI_Go_Hotel_MCP` | 自由行必含 |
| 📞 应急通讯录 | 知识储备 (航司/使馆/警察) | 跨境必含 |
| 📊 同价位竞品 | `MoreRecommendProductList` | 多产品对比必含 |
| 💱 实时汇率 | `ExchangeRate MCP` | 跨境必含 |
| 🛂 签证要求 | `wendao` + 知识储备 | 跨境必含 |

### 8.3 1 页模板预览 (让用户看实物)

**每套模板给一个 1 页 demo** (带灰色占位符), 用户看到实物才知道要补什么。

**示例 — trip-all-in-one.md 预览页** (Agent 自动展示):

```markdown
# {{目的地}} {{日期}} {{人数}}人 {{类型}}报告 V1

{{一句话结论}}

| 项 | 数据 |
|---|---|
| 报告生成 | {{YYYY-MM-DD HH:MM}} |
| 目的地 | {{城市, 国家}} |
| 出行日期 | {{YYYY.M.D - YYYY.M.D (N 天 M 晚)}} |
| 人数 | {{N 人私家团 / 自由行 / 跟团}} |
| 总预算 | {{¥XXXX-XXXX/人 或 ¥XXXXX-XXXXX/团}} |
| D-Day | 距离出发还有 {{D-N}} 天 |
| 必备准备 | ✅ X 份 PDF 已确认 / ⏳ X 待办 / 🔴 X 件必问 |

## §1 一句话结论
✅ 推荐: {{结论 + 排他理由}}
⚠️ 有条件: {{拿 N 件事答复再付尾款}}
❌ 不推荐: {{N 个红线问题}}
...
```

**3 套模板预览在 `templates/` 目录**, 加载时 Agent 自动展示。

### 8.4 多源智能补全映射 (用户给 1 份 → Agent 补 N 份)

| 用户给 | Agent 自动补 |
|---|---|
| 目的地 + 日期 | 高德 7 天天气 + wendao 实用信息 + 签证要求 + 紧急电话 |
| 机票 PDF | 真实航班时刻 + 准点率 + 兜底备选 + 航司历史风险 + 中转注意事项 |
| 酒店 PDF | 5 份订单交叉验证 + MCP 真实价位对比 + 售罄警告 + 平台价差 |
| 总预算 | 同价位竞品 8 个 + 价格日历 207 天 + 团费结构分解 |
| 行程单 | 逐日评分 + 强度评估 + 风险标注 + 季节性提示 |
| 卖家报价单 | 6 问追问清单 + 6 项优缺点模板 + 团费 ¥XXXX 拆解 |
| 餐厅偏好 | 7 天 7 列 35 家 (Google Maps 5 区域串行) |

### 8.5 触发词清单 (全场景)

**用户说下面任一, 加载本 skill**:

```
# 类型识别
"出旅游报告" / "出旅游的 PDF" / "帮我看看行程" / "检查行程"
"体检行程" / "行程有没有问题" / "优缺点" / "汇报型" / "给领导看"

# 模板 A
"出发前必读" / "出行全包" / "走 V5 模板" / "V5 风格" / "V5.1"

# 模板 B
"选哪个团" / "多产品对比" / "选型" / "对比" / "推荐一个"

# 模板 C
"帮我排行程" / "自由行规划" / "去哪好" / "行程设计"
```

**用户说下面任一, 加载 `ctrip-itinerary-review` skill** (本 skill 不接):
- "已有行程 + 体检 + 出 PPT" → `ctrip-itinerary-review` (走它自带 PPT pipeline)
- "已有行程 + 出 PDF" → **本 skill + 模板 A** (更通用)

---

## 9. 实战模板库 (2026-06-10 V5.1 沉淀 · 通用骨架)

> 3 套空白骨架 + 5 套设计模式 + 5 条思维原则。**零硬编码内容**, 只给结构和示例字段。

### 9.1 12 章节标准结构 (出行全包报告 · 模板 A)

不管目的地是{{目的地}}/东京/巴黎/马代, **任何出行全包报告都长这样**:

| § | 章节 | 必含字段 | 触发条件 | 模板优先级 |
|---|---|---|---|---|
| 1 | 封面 + 一句话结论 | 综合分/总成本/D-Day | 必有 | 必 |
| 2 | N 件必做 checklist | 必做事/截止/D-Day/状态 | 必有 | 必 |
| 3 | 全包行动表 (D1-Dn) | 日期/时间/事件/住宿/餐厅 | 行程 ≥ 3 天 | 必 |
| 4 | 交通现状 + 兜底 | 航班/车次/舱位/Plan B | 有跨城移动 | 跨城必 |
| 5 | 行程问题诊断 | 逐日评分 + 主要问题 + 建议 | 必有 | 必 |
| 6 | 住宿/资源档案 | 名称/地址/确认号/价格 | 有自订 | 有则必 |
| 7 | 优缺点汇总 | 6 项 ✅ + 6 项 ⚠️ | 必有 | 必 |
| 8 | 必问客服 N 件事 | 问题/触发原因/截止 | 必有 | 必 |
| 9 | 价格验证 | 已锁/待定/总成本 | 必有 | 必 |
| 10 | 实用信息 (出发前) | 签证/保险/必带/气候 | 跨境必含 | 跨境必 |
| 11 | 应急通讯录 + SOP | 12 个电话 + 6 步 SOP | 必有 | 必 |
| 12 | 数据来源 + 版本 | 字段/源/时间 | 必有 | 必 |

**章节顺序不可换** (叙事弧: 决策 → 行动 → 时间轴 → 资源 → 判断 → 风险 → 应急 → 来源)。
**章节可砍** (跨境不走 §10, 没自订跳 §6), **不可加** (用户没要求别加第 13 章)。

### 9.2 5 套设计模式 (通用, 不限场景)

遇到**这类内容**就**用这个模式** — 跨模板通用:

| 模式 | 适用 | 模板 (markdown) | M3 评分基线 |
|---|---|---|---|
| **A. D-Day 倒计时 checklist** | 必做/待办/行动项 | 表格 4 列: # / 事 / 截止 / D-Day | 9/10 |
| **B. 6 步骤 SOP 表格** | 取消/退票/延误/应急 | 表格 3 列: 步骤 / 时间窗 / 行动 | 9.5/10 |
| **C. 分级处置表** | 延误/风险/响应时间 | 表格 3 列: 时长 / 权益 / 行动 | 9/10 |
| **D. 全包行动表 (D1-Dn)** | 行程表 | 表格 5-6 列: 日期 / 时间 / 事件 / 住宿 / 餐厅 | 8.5/10 |
| **E. 优缺点 PRO/CON** | 综合判断 | 2 列 6+6 ✅/⚠️ | 8.5/10 |

**5 套模式完整示例在 `templates/patterns/` 目录** (5 个 .md 文件, 各自带字段占位符)。

### 9.3 5 条思维原则 (每次任务前过一遍)

不写死内容, 只写**"怎么想"**:

```
1. 砍冗余: 多源材料先列重复点, 砍到不重复 (V5: 5 项风险速览砍了, 3 份通讯录合 1)
2. 排序: 行动表/必做按时间倒推 (D-30 → D-1), 别按"重要性"乱排
3. 量化: 每个建议带 ¥ / 时间 / 截止, 不写空话 (例: "{{兜底票预算}} 兜底票" vs "建议买保险")
4. 兜底: 每个 Plan A 配 Plan B (航班/酒店/支付/签证), 不裸奔
5. 必问: 卖家/客服 6 问清单 → 筛 2-3 件最关键, 别问 30 条 (V4: V2 6 问 → V4 2 问)
```

**5 原则是 V5.1 实战总结**, 任何"出行报告"任务动手前先过一遍 → 报告质量基线 8/10 起。

### 9.4 模板目录 (3 套空白骨架 + 5 套模式)

```
templates/
├── trip-all-in-one.md         ← 模板 A: 12 章节空白骨架 (V5 风格)
├── multi-compare.md           ← 模板 B: 9 章节空白骨架
├── plan-from-scratch.md       ← 模板 C: 10 章节空白骨架
└── patterns/
    ├── d-day-checklist.md     ← 模式 A: 4 列 #/事/截止/D-Day
    ├── sop-6step.md           ← 模式 B: 3 列 步骤/时间窗/行动
    ├── delay-tier.md          ← 模式 C: 3 列 时长/权益/行动
    ├── day-by-day.md          ← 模式 D: 5-6 列 日期/时间/事件/住宿/餐厅
    └── pros-cons.md           ← 模式 E: 2 列 6+6 ✅/⚠️

references/
└── v5-case-study.md           ← V5.1 {{目的地}}实战案例 (5 个, 抽象化)

scripts/
└── verify-no-hardcoded.py     ← 模板零硬编码自验脚本 (grep 80+ {{目的地}}/航班/酒店/餐厅黑名单)
```

**所有模板都是空白骨架** (灰色占位符 `{{}}` 或 `<待填>`), **不带任何具体内容** ({{目的地}}/{{酒店名 A}}/{{酒店名 B}} 等都不会出现)。

**自验命令** (写完模板必跑):
```bash
/opt/data/.venv/bin/python /opt/data/skills/markdown-report-pdf/scripts/verify-no-hardcoded.py
```
**V5.1 实战教训**: 第一次跑抓到 6 处硬编码, 都是模板里写了"实战案例 (V5.1 {{目的地}})"段落 → 抽到 references/ 单独管理 → 模板里只写"见 references/v5-case-study.md 案例 X" → 0 违规。

### 9.5 使用流程 (5 步)

```
1. 用户说 "出旅游报告" / "体检行程" / "选哪个团"
        ↓
2. Agent 问 1-2 个关键问题识别类型 (A/B/C), 或用户直接说"走 V5"
        ↓
3. Agent 加载对应模板, 展示 1 页预览, 同时列"必填/选填/自动补"3 档追问
        ↓
4. 用户填字段 + 传文件 (支持分段喂, V1→V2→V3 迭代)
        ↓
5. Agent 套模板 → 走 pipeline (md_to_html + playwright + M3 vision) → 出 PDF
```

**时间预估**: 简单 (3 字段 + 1 文件) = 5 分钟; 中等 (8 字段 + 3 文件) = 15 分钟; 复杂 (迭代 V1→V4) = 30-60 分钟。

## 7. 组合交付:Markdown 报告 + Web PPT(2026-06-09 实战)

**触发**:用户既要看"打印/存档用 PDF",又要在"汇报/演示用 PPT 翻页",一份任务两份交付。

**模式**:
- **同一份内容**,两个出口
- **PDF**(本 skill):A4 印刷级,适合存档/打印/微信发送
- **Web PPT**(web-ppt-studio):横屏翻页,适合汇报/演示/团队预览
- 内容主体是 markdown 源,可双向 sync

**实战工作流**({{目的地}}行程体检,2026-06-09):
1. 写 `report.md`(主源,9 章)
2. 走本 skill pipeline → `report.pdf` (4 页 A4, 960KB, M3 vision 验证 8/10)
3. 同期走 web-ppt-studio → `index.html` (8 slide 翻页, 52KB)
4. 微信 send_message 时一并发送 `MEDIA:report.pdf` + `MEDIA:index.html`

**优势**:
- 用户手机刷到 PDF → 打印/转同事
- 电脑打开 HTML → 翻页演示,有 WebGL 背景 + 动画
- markdown 源 → 二次编辑只改一处

**陷阱**:
- PPT 不要把 markdown 全文照搬,要走 **8 slide 骨架**(封面 + 章节 + 数据 + 对比 + 收尾),每张 slide 是单页 max-density
- PDF 可放全文字;PPT 必须是**视觉密度低、信息少字**的杂志风
- 同一份数据,PDF 给详细数字({{尾款}} 尾款 4 位小数),PPT 只给 1-2 个 key number({{团费}})
