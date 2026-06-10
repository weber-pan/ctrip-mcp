# PDF 报告交付 / 下载分发踩坑集 (2026-06-07)

完整踩坑时间线 + 修复清单。当用户说"下载失败"/"下载服务器异常"/"打不开 PDF" 时,优先看这里。

## 1. 「下载服务器异常」= WebUI 前端 PDF.js 失败,不是 server 错

**用户报告**: "下载服务器异常"

**真正原因**(`/opt/data/hermes-webui/static/ui.js:8108-8143` 的 PDF 渲染链):

```
fetch /api/media?path=...pdf     (1.2MB 200 OK ✅)
  → pdfjsLib.getDocument({data:buf})  (❌ 15s CDN 超时 / CMap 字体 / CJK 字体不全)
  → page.render(canvasContext, viewport)  (❌ 渲染失败)
  → catch → fallback `<a download>` + i18n `pdf_error` = "下载服务器异常"
```

**用户看到"下载服务器异常"会误以为 server 挂了**,但实际:
- `curl -i http://localhost:8787/api/media?path=...&download=1` → **200 OK / 1.2MB / application/pdf / Content-Disposition: attachment**
- playwright `page.goto(...)` 看到 `Content-Disposition: attachment` 会抛 **`Page.goto: Download is starting`** = "已成功触发下载" 的标志
- 真正问题在浏览器 PDF.js 渲染链(cdn.jsdelivr.net 慢 / CJK 字体 / 解析失败)

## 2. 端口混淆: 9119 ≠ 8787

| Port | 服务 | 用途 |
|---|---|---|
| **9119** | `hermes dashboard` (hermes-agent 配置面板) | **不是** WebUI |
| **8787** | `hermes-webui` (真正 chat UI) | **才是** PDF / 文件下载来源 |

**症状**: `curl http://127.0.0.1:9119/api/media?path=...` → 401
**真正**: 9119 是 hermes-agent 的 CLI dashboard,没 `/api/media` endpoint
**解法**: 改用 `curl http://127.0.0.1:8787/api/media?path=...`

**验端口**:
```bash
ps -ef | grep "hermes dashboard" | grep -v grep
# hermes 100 31 0 /opt/hermes/.venv/bin/python /opt/hermes/.venv/bin/hermes dashboard --port 9119
cat /opt/data/home/.hermes/webui/bootstrap-8787.log
# [bootstrap] Starting Hermes Web UI on http://0.0.0.0:8787
```

## 3. 三种 100% 能下载 PDF 的方法(任选一)

### 方法 1 — 浏览器地址栏直链(最快)

复制下面到浏览器,直接弹下载框:

```
http://localhost:8787/api/media?path=/opt/data/home/workspace/<file>.pdf&download=1
```

`?download=1` 强制 `Content-Disposition: attachment`,浏览器走系统下载对话框。

### 方法 2 — WebUI 文件浏览器(用户最直观)

WebUI 左侧 **文件浏览器** → 找到 `.pdf` → 点 ··· → 下载

### 方法 3 — send_message 投递

文件已在 /tmp 或 /opt/data/home/workspace (这两个路径都在 `MEDIA_ALLOW_DIRS` allowlist),用 `send_message` 投递:

```python
send_message(message='MEDIA:/opt/data/home/workspace/xhs_ctrip_bali_report_v3.pdf')
```

## 4. PDF 渲染的 PyMuPDF 路径(验中文 + 验排版)

```python
# 装在 /opt/data/.venv (不是 /opt/hermes/.venv)
import subprocess
subprocess.run(['/opt/data/.venv/bin/pip', 'install', '-q', 'PyMuPDF'], check=True)

import fitz
doc = fitz.open('/opt/data/home/workspace/xhs_ctrip_bali_report_v3.pdf')
print(f'页数: {len(doc)}, is_encrypted: {doc.is_encrypted}')  # 7, False
for p in doc:
    print(p.get_text()[:200])  # 中文完整 = 字体 OK

# 渲首页 PNG 给 M3 vision 看
doc[0].get_pixmap(dpi=110).save('/tmp/preview_p1.png')
```

## 5. M3 vision 验渲染(用 m3-native-vision,不用 vision_analyze 工具)

```python
# /opt/data/.env 拿 key
env = {}
for line in open('/opt/data/.env'):
    line = line.strip()
    if line and not line.startswith('#') and '=' in line:
        k, v = line.split('=', 1); v = v.strip()
        if (v.startswith("'") and v.endswith("'")) or (v.startswith('"') and v.endswith('"')):
            v = v[1:-1]
        env[k.strip()] = v

import os, json, urllib.request, base64, ssl
key = env['MINIMAX_CN_API_KEY']; base = env['MINIMAX_CN_BASE_URL']
img_b64 = base64.standard_b64encode(open('/tmp/preview_p1.png', 'rb').read()).decode()
body = {"model": "MiniMax-VL-01", "max_tokens": 800,
        "messages": [{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": img_b64}},
            {"type": "text", "text": "请简短回答:1) 中文是否正常无乱码?2) 排版是否清晰?3) ✅/❌ 行色块强度(1-10)?4) 整体评分 0-10。"}]
        }]}
req = urllib.request.Request(base + '/v1/messages',
    data=json.dumps(body).encode('utf-8'),
    headers={'Content-Type': 'application/json', 'x-api-key': key,
             'anthropic-version': '2023-06-01'})
with urllib.request.urlopen(req, timeout=60, context=ssl.create_default_context()) as resp:
    r = json.loads(resp.read())
    for c in r['content']:
        if c['type'] == 'text': print(c['text'])
```

## 6. 调色 5 轮实战经验(2026-06-07)

| 轮 | 改动 | M3 评分 | 经验 |
|---|---|---|---|
| 1 | 基础(白底) | 7.5 | 起步线 |
| 2 | 加 row-ok/x 浅底 | 6.5 | 浅色对比弱**反而降分** |
| 3 | row-ok/x 加粗 + 加深 | 7.5 | 加粗修复 |
| 4 | row-ok/x 加 3pt 左色条 + 加深 | 7.5 | 视觉锚点 |
| 5 | h2 加浅蓝底 block | — | 章节区分 |

**结论**:
- 1 次色要深:`#c00000` (深红) + `#2e7d32` (深绿) + 3pt 左侧色条 = 醒目
- 浅色底 (`#f0faf4`) 永远不够,**至少** `#d4edda` 起
- `border-left: 3pt solid` 是色条之王, 比加色块更省空间
- 不要在第 1 轮就调到位,**先问 M3 评分,再**迭代,不要盲调
