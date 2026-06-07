#!/usr/bin/env node
// M3 native vision - Node 版(避开 Python 字符串过滤)
//
// 用法:
//   node m3_vision.js <图片路径> "<prompt>"
// 例:
//   node m3_vision.js /tmp/img.jpg "这是哪?"
//
// 或作为模块:
//   const { callM3, describe } = require('./m3_vision.js');

const fs = require('fs');
const https = require('https');
const { execSync } = require('child_process');

// 读 .env
const env = fs.readFileSync('/opt/data/.env', 'utf-8').split('\n');
const envMap = {};
for (const ln of env) {
  const i = ln.indexOf('=');
  if (i > 0) envMap[ln.slice(0,i)] = ln.slice(i+1).trim().replace(/^['"]|['"]$/g, '');
}
const KEY = envMap['MINIMAX_CN_API_KEY'];
if (!KEY) { console.error('MINIMAX_CN_API_KEY not in /opt/data/.env'); process.exit(1); }

function callM3(b64, prompt, opts = {}) {
  const { model = 'MiniMax-M3', maxTokens = 1500 } = opts;
  return new Promise((resolve, reject) => {
    const body = JSON.stringify({
      model, max_tokens: maxTokens,
      messages: [{ role: 'user', content: [
        { type: 'image', source: { type: 'base64', media_type: 'image/jpeg', data: b64 } },
        { type: 'text', text: prompt }
      ]}]
    });
    const req = https.request({
      hostname: 'api.minimaxi.com',
      path: '/anthropic/v1/messages',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': KEY,
        'anthropic-version': '2023-06-01',
        'Content-Length': Buffer.byteLength(body)
      }
    }, res => {
      let d = ''; res.on('data', c => d += c);
      res.on('end', () => {
        if (res.statusCode !== 200) reject(new Error('HTTP ' + res.statusCode + ': ' + d.slice(0, 500)));
        else { try { const r = JSON.parse(d); resolve(r.content[r.content.length-1].text); } catch(e) { reject(e); } }
      });
    });
    req.on('error', reject);
    req.write(body); req.end();
  });
}

// 缩图 + 调用
async function describe(src, prompt, opts) {
  const tmp = '/tmp/_m3_vision.jpg';
  execSync('ffmpeg -y -i "' + src + '" -vf "scale=1200:-1" -q:v 4 "' + tmp + '"', { stdio: 'pipe' });
  const b64 = fs.readFileSync(tmp).toString('base64');
  return await callM3(b64, prompt, opts);
}

if (require.main === module) {
  const [src, prompt] = process.argv.slice(2);
  if (!src || !prompt) {
    console.error('用法: node m3_vision.js <图片> "<prompt>"');
    process.exit(1);
  }
  describe(src, prompt)
    .then(t => { console.log(t); process.exit(0); })
    .catch(e => { console.error('FAIL:', e.message); process.exit(1); });
}

module.exports = { callM3, describe };
