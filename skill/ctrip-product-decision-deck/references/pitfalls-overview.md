# 关键 pitfall 总览 (2026-06-07 v4 综合)

> 各专题 pitfall 散落在多个 references, 这里汇总 + 加新发现

## 1. Playwright 抓 graphql 的 4 大坑 (ctrip-shopping-detail.md 已详)
1. URL 必须拼 `&shoppingid=32hex`
2. `page.on('response')` 不可靠, 改 `expect_response`
3. expect_response 一次只能等一个, 循环 2 次
4. shoppingid 从上次 e2e 抓的 json 拿, fallback hard-code

## 2. SVG 渲染坑 (svg-pitfalls.md)
- `&` 未转义
- `marker-end` 无 `<marker>` 定义
- `symbol + use` 引用 svg_to_pptx 失败
- spec_lock 颜色穷举遗漏
- 同一元素 2 个 font-size
- **image href** 两种方式: 绝对路径 (v1-v3) / base64 (v4 ✓)
  - **v4 实测**: 9 张 base64 + 28 页 = 2.43 MB PPTX ✓
  - **不要** `file:///` / 相对路径 / 中文 `\u` escape

## 3. 工具/编码坑 (2026-06-07 新)
- **write_file 截断 `*`**: `MINIMAX_CN_API_KEY=***` 中 `*` 被转义, 写 Python heredoc 失败
  - 修法: **用 Node 读 .env + base64**, 或用 `\\` escape
- **skill_manage patch 路径**: 默认改 SKILL.md, 要 patch references/ 必须给 `file_path` 参数
  - 错: `skill_manage(action='patch', name=..., old_string=...)` ← 改 SKILL.md
  - 对: `skill_manage(action='patch', file_path='references/xxx.md', name=..., old_string=...)`
- **skill_view + read_file 限制**: background review 模式只允许 memory + skill_manage, 不能 read_file/terminal
- **execute_code "import inspect" 陷阱**: /tmp/inspect.py 抢占 stdlib, 删除后才能跑
- **M3 vision API**: 直接调 `api.minimaxi.com/anthropic/v1/messages` + CN key, **不要用** `mmx CLI` (报 balance 错) 或 `vision_analyze` (server 404)

## 4. 携程数据坑
- `imageHotelList` 9 家 ≠ 真实入住, 真实住 5 晚在**图文日历**
- m 端 SPA URL 只带 productId + departCityId, 没日期
- m 端默认展示"最近班期", 用户实际班期是页面下拉选的
- 携程 `m.ctrip.com/restapi/soa2/14552/*` 匿名 = 11010 Forbidden
- 携程 `getCommentList` 公开 = 403 反爬
- 替代: AI_Go_Hotel_MCP 公开源 (5 家 100% 拿 hotelId+房型+价)

## 5. 用户 cookie 拒收 (2026-06-07 user 误贴 BDUSS)
- BDUSS_BFESS = 百度账号长期凭证, 跟携程任务无关域
- 必拒 + 解释
- 替代: Booking.com / TripAdvisor / Google Maps 公开源

## 6. 兄弟 subagent 并发坑
- 多 subagent 并发 patch 同一文件 = race condition, 丢改动
- **串行** + 整文件 read 后再 patch 才稳
- 兄弟 subagent 改的文件再次 patch 会报 "sibling subagent modified"

## 7. memory 容量限制
- 当前 94% 满 (2086/2200 字符)
- 不要重复记"v4 升级了 SKILL"等一次性事件
- 只记:环境坑 / 用户偏好 / 工具特性 / 持久事实

## 8. SKILL.md 同步 3 路
- `/opt/data/skills/ctrip-product-decision-deck/` (主)
- `/opt/data/home/.hermes/skills/...` (home)
- `/opt/data/hermes-agent/skills/...` (agent)
- 三路用**硬链** (同 inode), 改一处自动同步
- 验证: `stat -c '%i %n'` 看 inode
- 文件在 3 路, 但 SKILL.md 描述在 system prompt 是另一份 cache, 改完跑 `clear_skills_system_prompt_cache(clear_snapshot=True)` 才生效
