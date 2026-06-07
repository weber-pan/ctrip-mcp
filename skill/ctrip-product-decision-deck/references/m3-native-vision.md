# M3 Native Vision (Direct minimax API)

**关键发现**: Hermes 内置 `vision_analyze` 工具 **会挂** (404/nginx)。**别用它**。

**真正可用的视觉通道**: 直接调 minimax Messages API(走 CN anthropic 兼容端点)。

## 调用模板 (Node,避免 Python 字符串转义)

```javascript
const fs = require('fs');
const env = fs.readFileSync('/opt/data/.env','utf-8').split('\n');
const envMap = {};
for (const ln of env) {
  const i = ln.indexOf('=');
  if (i > 0) envMap[ln.slice(0,i)] = ln.slice(i+1).trim().replace(/^['"]|['"]$/g, '');
}
const key = envMap['MINIMAX_CN_API_KEY'];  // 走 anthropic 兼容

const https = require('https');
function callM3(b64, prompt) {
  const body = JSON.stringify({
    model: 'MiniMax-M3',
    max_tokens: 1500,
    messages: [{ role: 'user', content: [
      { type: 'image', source: { type: 'base64', media_type: 'image/jpeg', data: b64 } },
      { type: 'text', text: prompt }
    ]}]
  });
  return new Promise((resolve, reject) => {
    const req = https.request({
      hostname: 'api.minimaxi.com',
      path: '/anthropic/v1/messages',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': key,
        'anthropic-version': '2023-06-01',
        'Content-Length': Buffer.byteLength(body)
      }
    }, res => {
      let d = '';
      res.on('data', c => d += c);
      res.on('end', () => {
        if (res.statusCode !== 200) reject(new Error('HTTP '+res.statusCode+': '+d.slice(0,500)));
        else { const r = JSON.parse(d); resolve(r.content[r.content.length-1].text); }
      });
    });
    req.on('error', reject);
    req.write(body); req.end();
  });
}
```

## 三大坑

1. **图大小限制**: 单图 10 MB / 请求体 64 MB / 视频 50 MB(URL/base64)
2. **413 处理**: 原图直接传会 413,**用 ffmpeg 缩**:
   ```bash
   ffmpeg -y -i input.jpg -vf "scale=1200:-1" -q:v 4 /tmp/med.jpg
   ```
3. **不要用 Python 多行字符串**: Hermes token 过滤会把 `*` 等特殊字符处理掉,导致 SyntaxError。**用 Node 数组 + 字符串拼接**,或 base64 读 .env

## 提取 prompt 模板

```javascript
const prompt = '这是携程产品宣传 banner。完整逐字提取图中所有文字,然后回答:1)产品名/标题 2)行程天数+路线 3)价格/优惠 4)增值服务 5)团队规则 6)品牌 7)电话/二维码/促销码。按原样,看不清的标 [模糊]'
```

**M3 视觉特点**:
- 中文 OCR 极强(中文 800+ 字无错)
- 行程信息/营销话术都能读
- 颜色/构图/氛围判断准确
- 单张图 ~800-1500 tokens

## 配额参考

- CN key 走 anthropic,quota 充足(2026-06-07 查 general 槽 100%)
- mmx CLI `vision describe` 报 "insufficient balance" — **是它走错 key,不是余额真不够**
- 优先用 .env 里的 `MINIMAX_CN_API_KEY` 直接 curl

## 适用场景

- 携程 banner 文字/行程提取
- POI 景点内容识别
- 酒店档次判断
- 游客实拍图场景还原
- 任何需要"AI 视觉读图"的场景(Hermes vision_analyze 挂掉时的备胎)