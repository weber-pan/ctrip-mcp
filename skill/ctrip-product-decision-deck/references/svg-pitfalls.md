# SVG 4 大坑 + 修法

> 来源: case-study-bali-2026-06-05 + case-p69762187-2026-07-04

## 坑 1: `&` 未转义

**症状**:
```
[ERROR] Invalid XML: not well-formed (invalid token): line 76, column 131
```

**原因**: SVG 是 XML,`&` 必须写 `&amp;`:
```xml
<text>总距离 & 时间预算</text>      ❌
<text>总距离 &amp; 时间预算</text>  ✅
```

**自检命令**:
```bash
grep -nP '[^&;](&)[^a-z#]' svg_output/*.svg
```

**修法**:
```bash
# 用 sed 批量改(单文件场景)
sed -i 's/& /\&amp; /g' file.svg
```

## 坑 2: `marker-end="url(#xx)"` 无 `<marker>` 定义

**症状**:
```
[ERROR] Detected marker-start/marker-end referencing a marker id,
       but no <marker> element found in the file
```

**原因**: SVG 用了箭头标记但没在 `<defs>` 里定义:
```xml
<line ... marker-end="url(#arrow)"/>  ❌
<defs>
  <marker id="arrow" ...>...</marker>
</defs>
<line ... marker-end="url(#arrow)"/>  ✅
```

**修法**:
- 简单场景: 改纯 `<line>`(去掉 marker)
- 复杂场景: 在 `<defs>` 里加 `<marker>`

## 坑 3: `symbol + use` 引用 + svg_to_pptx 失败

**症状**:
```
Converted 0 elements, skipped 5
```

**原因**: ppt-master 转 svg_to_pptx 对 `<symbol>/<use>` 支持差。

**修法**: 改 inline 元素(展开所有 `<use>` 引用)

## 坑 4: spec_lock 颜色穷举遗漏

**症状**:
```
spec_lock drift: 8 color(s), 3 font-family value(s) not in spec_lock.md
```

**原因**: SVG 用了 17+ 颜色,但 spec_lock.md 只列了 10 个。ppt-master 要求**每个用到的颜色都登记**。

**修法**:
1. 先写 `spec_lock.md`(穷举 13+ 色 + 3 字体 stack)
2. 后写 SVG(只允许用 spec_lock 里的)
3. 加新色 → 先更新 spec_lock

## 坑 5: 同一元素 2 个 `font-size` 属性(xml.etree 拒绝,2026-06-07 新)

**症状**:
```
xml.etree.ElementTree.ParseError: duplicate attribute: line 26, column 72
```

**原因**: 复制模板时把 `font-size` 误重复 2 次:
```xml
<text font-size="11" font-weight="bold" fill="#3E6B53" font-size="20">  ❌
<text font-size="20" font-weight="bold" fill="#3E6B53">                    ✅
```

**修法**:
- 删一个 `font-size` 属性
- 用 grep 自检: `grep -nP 'font-size.*font-size' svg_output/*.svg`

## 坑 6: SVG `<image href>` 路径用相对路径(2026-06-07 新)

**症状**: PPT 渲染时图不显示,或 `convert_svg_to_slide_shapes` 报 "image not found"

**修法**:
- **必须绝对路径** `/opt/data/ctrip-data/img_<pid>/desc_0.jpg`
- 复制图到 ppt-master `images/` 后用 `../images/xxx.jpg` 或 `file:///...` 三种
- **不要 base64 嵌大图**(25 页 × 300KB = 7.5MB,PPTX 卡)
- 中文路径(佩妮达岛.jpg)unicode 直接写,不要 `\u` escape

## 跑命令前必查

```bash
# 1. 跑 quality_checker (0 error)
/opt/data/.venv/bin/python scripts/svg_quality_checker.py <项目>

# 2. 看输出, 用 grep 找 ERROR
... | grep -A 5 "ERROR"

# 3. 修 → 再跑 → 0 error 才进 finalize
```

## 全部 0 error 后

```bash
/opt/data/.venv/bin/python scripts/finalize_svg.py <项目>
/opt/data/.venv/bin/python scripts/svg_to_pptx.py <项目>
```

`Succeeded: 21, Failed: 0` 才算完工。
