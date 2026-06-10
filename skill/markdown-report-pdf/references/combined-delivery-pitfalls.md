# 组合交付:Markdown 报告 + Web PPT — 实战踩坑(2026-06-09)

## 完整流程(从任务接收到微信推送)

```
1. 写 report.md (主源,9 章)              ← 1 个 write_file
2. 跑 markdown-report-pdf pipeline        ← md → HTML → PDF
3. 同期跑 web-ppt-studio                  ← 8 slide 翻页 PPT
4. 视觉验证:M3 vision 跑 PDF 首页         ← 验中文+排版
5. 微信 send_message 一并发送              ← MEDIA:report.pdf + MEDIA:index.html
```

## 典型耗时
- write_file report.md: 30s
- pipeline 跑通(md → HTML → PDF):1-2 min
- 视觉验证 PNG + M3 API call:30-60s
- 同期做 PPT(8 slide 设计 + 改):3-5 min
- 微信推送:30s(算上退避)
- **总耗时 5-8 min**

## 文件命名规范(用户能看到"专业"程度)

```
/opt/data/home/workspace/ppt-output/<topic-slug>/
├── report.md            ← 主源(可编辑)
├── report.html          ← HTML 中间态(给 PPT 改时用)
├── report.pdf           ← ⭐ 主交付 PDF
└── index.html           ← 8 slide 翻页 PPT
```

## 5 个常见坑

### 1. PDF 渲染中文乱码
**症状**: PDF 里中文显示为方块 / 框线
**原因**: 没用 WQY 字体 / playwright evaluate 字体 ready 漏了
**解法**: `fc-list :lang=zh` 确认有 WenQuanYi Micro Hei,playwright 里加 `page.evaluate("document.fonts.ready")`

### 2. PPT 标题栏显示 `[必填]...`
**症状**: 浏览器 tab 标题或页面 hero 区是 `\[必填\].*` 字面量
**原因**: 忘了跑 `sed -i 's|<title>\[必填\].*</title>|<title>...</title>|' index.html`
**解法**: grep `[必填]` 应该 0 个,或直接用 `set -e` 改完就校验

### 3. 8-slide-deck-style-a.html 误用为模板
**症状**: 浏览器渲染出 markdown 注释 + section 文字,没样式
**原因**: 这个文件**只是 8 个 `<section>` 片段,不是完整 HTML**
**解法**: cp `template.html` (858 行,含 head + body + WebGL) 而不是 8-slide-deck-style-a.html(221 行,只是片段)

### 4. Vision 反馈 row-ok/row-x 颜色对比度弱
**症状**: M3 vision 评分 6-7 分,说"色块对比度不够"
**原因**: 浅色底(默认 `#f0faf4`)在白纸上对比度不足
**解法**: 加深 + 加左侧色条:
```css
tr.row-ok td { background: #d4edda; color: #0d4a1f; font-weight: 600; border-left: 3pt solid #2e7d32; }
tr.row-x td  { background: #fcd5d5; color: #5a0a0a; font-weight: 600; border-left: 3pt solid #c00000; }
```

### 5. 微信推送限流
**症状**: `iLink sendmessage rate limited: ret=-2 errcode=None errmsg=rate limited`
**原因**: 连续发送触发 iLink 限流(同 chat 30-60s 内多条)
**解法**: 
- 单条 send 即可,不要一次发多条
- 失败后等 30-60s 再试,不要立即重试
- 准备 2-3 个备选 chat target(target='weixin' / 完整 chat_id)
- 实在推不上去 = 改用 `MEDIA:` 路径告诉用户文件位置,用户本地打开

## 视觉验证(M3 vision 调用模板)

```bash
node /opt/data/ctrip-mcp/skill/ctrip-product-decision-deck/scripts/m3_vision.js \
  /tmp/report_p1.png \
  "请简短回答:1) 中文是否正常无乱码?2) 排版是否清晰?3) 表格是否整齐?4) ✅❌行色块对比度(1-10)?5) 整体评分 0-10。6) 给出 3 条改进建议。"
```

8/10 以上 = 可交付,7-8 分 = 视情况交付,7 分以下 = 调色重出。

## 报告 vs PPT 的内容密度差异(经验值)

| 维度 | 报告 PDF | Web PPT |
|---|---|---|
| 每页字数 | 200-400 字 | 5-30 字 |
| 数字精度 | 完整({{尾款}}.00) | 取整({{尾款}}) |
| 表格 | 完整多列表 | 简化 2-3 列 |
| 配图 | 不放(可选) | 必须有(占 60% 视觉) |
| 适合场景 | 打印 / 存档 / 细读 | 投影 / 演示 / 翻页 |
| 视觉风格 | 严肃 / 文档 | 杂志 / WebGL 背景 |
