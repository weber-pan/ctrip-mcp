#!/usr/bin/env node
/**
 * wendao_weather.js — 7 天天气预报查询包装
 * 
 * 用法:
 *   node wendao_weather.js                      # 默认 上海 + 亚庇, 7/4-7/10
 *   node wendao_weather.js 上海 成都 2026-07-01 2026-07-07
 *   node wendao_weather.js "东京" "大阪" "2026-08-01" "2026-08-07"
 * 
 * 输出: markdown 格式天气对照表,直接 stdout
 * 依赖: /opt/data/scripts/wendao_query.js (wendao API Node 包装)
 */
const { spawn } = require('child_process');
const path = require('path');

const WENDAO = '/opt/data/scripts/wendao_query.js';

const args = process.argv.slice(2);
let cityA = '上海', cityB = '亚庇', startDate = '2026-07-04', endDate = '2026-07-10';

if (args.length >= 1) cityA = args[0];
if (args.length >= 2) cityB = args[1];
if (args.length >= 3) startDate = args[2];
if (args.length >= 4) endDate = args[3];

// 计算天数
function daysBetween(s, e) {
  const a = new Date(s), b = new Date(e);
  return Math.round((b - a) / 86400000) + 1;
}
const days = daysBetween(startDate, endDate);

const query = `${cityA} 和 ${cityB} ${startDate} 至 ${endDate} 共${days}天每天天气预报,包括:最高温/最低温/降雨概率/湿度/风速/紫外线指数/台风风险,做成对照表,每城市一列`;

function runWendao(q) {
  return new Promise((resolve, reject) => {
    const child = spawn('node', [WENDAO, q], {
      cwd: '/opt/data',
      stdio: ['ignore', 'pipe', 'pipe']
    });
    let stdout = '', stderr = '';
    child.stdout.on('data', d => stdout += d);
    child.stderr.on('data', d => stderr += d);
    child.on('close', code => {
      if (stdout.trim()) resolve(stdout.trim());
      else if (stderr.trim()) resolve(stderr.trim());
      else resolve('');
    });
    child.on('error', reject);
    // 90s 超时
    setTimeout(() => { child.kill(); resolve(''); }, 90000);
  });
}

(async () => {
  const result = await runWendao(query);
  if (!result) {
    console.log(`⚠️ wendao 未返回天气数据(90s 超时或空响应)`);
    process.exit(1);
  }
  console.log(`# 🌤️ ${startDate}–${endDate} 天气预报\n`);
  console.log(`| 日期 | ${cityA} | ${cityB} | 出海建议 |`);
  console.log(`|---|---|---|---|`);
  // wendao 返回格式不固定,直接打印原文
  console.log(result);
})();