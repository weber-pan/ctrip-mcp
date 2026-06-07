---
name: api-limitations
description: API 反爬 / 第三方限制 = 真实瓶颈,标"无解"+具体技术原因,不糊弄"再查查"
---

# API 反爬 = 真实瓶颈(诚实标注规范)

> 2026-06-07 用户原话: "接口反爬就是无解, 不是再查查"。
> 禁止说"再查查" / "试试别的方式" / "可能可以" — 真无解就写"无解"。

## §1 原则

| 情况 | ❌ 错 | ✅ 对 |
|---|---|---|
| API 不返分页 | "试试分页参数" | "接口不返分页参数,7 条点评无法拿全" |
| server OAuth 挂 | "再试一次" | "server 端 404 Invalid session id,本次失败" |
| 浏览器反爬 | "换浏览器" | "Trip.com 触发反爬,无法浏览器抓" |
| Google 拦截 | "换关键词" | "Google sorry 拦截, 改 Bing" |

**核心**: 写**具体技术原因** + **尝试过什么**,不是"再去查查"。

## §2 真实瓶颈 2 案例(本次 p69762187)

### 瓶颈 1 · 点评时间分布

**症状**: 8 条点评,只能拿到 1 条时间戳

**根因**:
- 携程 `getCommentSummary` 一次性只返 `comments[]` 长度=1
- `totalCount=8` 但前 7 条不返(反爬设计)
- **无分页参数** = 接口故意只给前 1 条

**尝试过的方法**:
- 查 `extInfo.extInfoMap` 内部 → 找到 `takeoffDate/returnDate` (已用)
- 查 `attachments` 数组 → 只给图片数,无时间
- 查 `subItems` / `subItemTags` → 评分标签,无时间

**结论**: 拿全 8 条需分页 API(无参数 = 反爬),**非"再查查"**。

**报告标注**:
```
P22 客群画像: 1 条样本 (2026-03-28 团 真实起飞日)
+ extInfo 真实样本 + 标明"接口反爬"瓶颈
```

### 瓶颈 2 · 航班独立第三方交叉

**症状**: wendao = 携程缓存,不算真正独立

**根因**:
- `variflight-mcp getFlightTransferInfo` → 404 Invalid session id (server OAuth 挂)
- `Trip.com` 浏览器抓 → 触发反爬
- `FlightConnections` 浏览器抓 → JS 加载慢且数据需登录

**尝试过的方法**:
- 重试 variflight 3 次 → 持续 404
- 浏览器抓 Trip.com 航班查询 → 触发反爬
- Bing 搜 "SHA→SUB 2026-07-04 航班" → 搜索结果无实时数据

**结论**: 真正独立第三方源无法获取,**只用"携程主接口 × wendao"双源一致** 当间接交叉。

**报告标注**:
```
P04 v2: 双源一致 (携程主接口 = wendao 5 班次) → 间接交叉,非真正独立
         variflight 不可用 (server OAuth 404)
```

### 瓶颈 1.5 · `extInfo.extInfoMap` 隐藏字段套取(通用技巧,2026-06-07 补)

**症状**: 顶层 `comments[]` 只给 1 条,`totalCount=N` 拿不全

**解套**: 携程 `getCommentSummary` 单条 `extInfo` 字段虽然返 dict,但**深层 `extInfoMap` 里常含其他点评的隐式时间戳**:

```python
c = d['comments'][0]
ext = c['extInfo']['extInfoMap']   # ← 不是字符串!是 dict
ext['takeoffDate']    # 1774627200000 → 2026-03-28 真实起飞日
ext['returnDate']     # 1775145600000 → 2026-04-03 真实返程日
ext['startCityName']  # 真实出发地
ext['destCityName']   # 真实目的地
ext['vendorId'] / 'biVendorId'  # 真实供应商 ID
ext['productCategoryId']  # 11=私家团 / 12=跟团游
ext['tourType']       # 1=朋友 / 2=家庭 / 3=蜜月
```

**其他可解套字段**(注意可能是 JSON 字符串,要双层 `json.loads`):
- `userInfo` dict: 等级 (铂金/钻石)、马甲名、头像
- `tourTypeInfo` dict: `tourType:1` + `tourTypeName:"朋友出游"`
- `attachments` / `subItems` / `subItemTags` 可能是 JSON 字符串

**结论**: **反爬时先去 `extInfo.extInfoMap` 偷** 4-5 个真实字段,够用就行,不要硬拿全 N 条。

## §3 写 PPT / 报告时的标注格式

```markdown
## 数据来源 (按真实度)

### ✅ 主源 (e2e 核实)
- 携程 SPA xhr: 价格 / 班期 / 酒店 / 真实点评 1 条

### ⚠ 间接源 (携程缓存+AI 总结)
- wendao: 气候 / 火山政策 / 真实评价 / 转车
- wendao 5 班次: 验证携程主接口航班(双源一致,间接交叉)

### ❌ 无解 (真实瓶颈, 不可糊弄)
- 点评 7 条时间分布 → API 反爬,无分页参数
- 航班真正独立第三方交叉 → variflight server OAuth 挂 + Trip.com 浏览器反爬
```

## §4 用户对"伪解决"0 容忍

❌ **绝对禁止**:
- "已查,未找到" (不说具体技术原因)
- "可能可以试试分页" (试探性)
- "如果需要可以再查" (甩锅)
- "wendao 已验证" (误导,实际是携程缓存)

✅ **必须**:
- 写**具体 API 名 + 错误码 + 已尝试的方法**
- 区分**"未尝试"** vs **"已尝试无解"** vs **"有解但本次不做"**
- 真正无解时**直接说"无解"**,提供 fallback(用户可决定要不要换路径)
