# 真实酒店提取 — 图文日历 + hotelList 链接(2026-06-07 新)

> 用户原话: "你没看到 这里的酒店吗 你不能点击进去看到详情吗" + "那你现在能拿到 酒店信息 可以 去查具体的评价这些吗"
>
> **核心教训:e2e 抓的 `imageHotelList` ≠ 真实入住**。**真实入住在图文日历**,且**hotelList 链接里嵌 SH hotelId 可用 AI_Go_Hotel_MCP 公开查**。

## 1. 致命坑:e2e 抓的"酒店字段"是营销标签

**症状**:
- e2e 抓的 `xhr_ProductInfo_2nd_V3` JSON 里 `TravelIntroductionInfo.HotelInfoList` 全部 = `"自选酒店(4钻及以上)"`(营销标签)
- `xhr_ImageList_2` 抓到的 `imageHotelList` 是 **9 家"备选"** 营销图集,**不是真实入住**
- 真实行程是**分散住 5 晚**:**跟景点走** — 泗水进 → 庞越(布罗莫) → 外南梦(伊真) → 巴厘岛罗维纳(海豚) → 库塔(市区送机)

**修法**:
- 永远**先看图文日历**(用户发的日历格式) → 那 5 晚 = 真实入住
- 真实行程判断:**5 晚住 5 个不同酒店** = 跟团游典型,**集中住 1 个 5 星** = 高端团
- P06 真实酒店页**必须基于图文日历**,不能用 imageHotelList 9 家

## 2. hotelList 链接解析:拿 SH hotelId

携程图文日历的"更换酒店"按钮 URL 模板:

```
https://vacations.ctrip.com/idiytour-simple/hotelList
  ?shoppingId=<32-hex>          # 购物车 ID
  &roomtoken=02_H1542841_R1348325428_I2026-07-04_O2026-07-05_C37354904861_RatePlan645243902_SP0_RP279_SH104048857_SID0_...
  &segment=2                     # 第几段(Segment 0-indexed)
  &sourcefrom=tour_channel
  &from=...
```

**关键字段**:
- `SH104048857` → **hotelId 104048857**(每段 1 个 SH)
- `_I2026-07-04_O2026-07-05_` → 该段入住/离店日期
- `SID0_` → segment 序号
- `RP279` → 参考价 ¥279
- 5 段 roomtoken = 5 个不同 SH hotelId(每晚换酒店)

**用法**:
1. 用户贴 1 段 URL → 改 `SHxxx` 数字 + `_I`/`_O` 日期 + `segment=N` 查其他 4 段
2. 用 hotelId 调 `AI_Go_Hotel_MCP.getHotelDetail(hotelId=N)` 拿真实点评+房型+7/4 价格

## 3. AI_Go_Hotel_MCP 公开查 5 家酒店(免 cookie 免登录)

**MCP server**: `AI_Go_Hotel_MCP`(amap 后端,公开数据池)

**searchHotels** 模板:

```js
{
  "originQuery": "桑提卡 Gubeng 4 钻 不可取消",
  "place": "Hotel Santika Premiere Gubeng Surabaya",  // 英文名!
  "placeType": "酒店"
}
```

**关键点**:
- **`place` 写英文全名**(中文名常搜成"呼和浩特固本"等误配)
- 5 家全搜到 hotelId 后,逐个 `getHotelDetail(hotelId=N)` 拿当日房价
- 返回数据完整:**hotelId / 星级 / 最低价 / 经纬度 / 距机场 / 距景点 / 设施清单 / 描述 / imageUrl**
- 全部有 imageUrl,可 curl 下载(curl 走 aigohotel.com CDN,不是 m.ctrip.com,无 403)

**5 家案例(p69762187)**:

| 夜 | 酒店 | hotelId | 星级 | 最低价(¥/晚) | 关键距离 |
|---|---|---|---|---|---|
| 7/4-5 | 桑提卡 Gubeng 4 钻 125 评 4.6/5 | `154486` | 4 星 | 235 | 距 SUB 19.1km / Tunjungan 广场 2.1km |
| 7/5-6 | 布罗莫公园 3 钻 72 评 4.1/5 | `610893` | 3 星 | 215 | 庞越市区 |
| 7/6-7 | 外南梦 El 皇家 4 钻 93 评 4.7/5 | `420772` | 4 星 | 201 | 距 BWX 11.7km / 巴努旺吉公园 0.2km |
| 7/7-8 | 罗威纳海滩俱乐部 4 钻 212 评 4.2/5 | `248554` | 3.5 星 | 411 | 海边 / 距罗维纳海滩 3.9km / 距 DPS 93.2km |
| 7/8-10 | 库塔万枫 4 钻 421 评 4.4/5 | `1160562` | 3 星 | 276 | 距 DPS 6.3km / 距库塔海滩 2.4km |

**5 晚总房费 ≈ ¥1,614/人**(单人占单间)或 ¥3,228(双人标间)

## 4. 真实数据 vs 营销标签的判定表

| 字段源 | 类型 | 可信度 | 用途 |
|---|---|---|---|
| **图文日历**(用户发) | 真实入住 | ⭐⭐⭐⭐⭐ | P06 真实酒店主图 |
| `getHotelDetail(hid)` | 当日房价/房型 | ⭐⭐⭐⭐ | P07 价格日历 / P08 最低价 |
| `imageHotelList` (e2e) | 营销图集 | ⭐⭐ | P06 备选池(放底部) |
| `HotelInfoList` "自选酒店(4钻及以上)" | 营销标签 | ⭐ | 不用 |

## 5. 不可取消 3 晚 = 风险窗

真实行程中,标注"不可取消"的酒店 = 退订无救,**必须标红**到 P06:

- **桑提卡 Gubeng**(7/4-5)= 不可取消
- **罗威纳海滩俱乐部**(7/7-8)= 不可取消
- **库塔万枫**(7/8-10)= 不可取消
- 2 晚可取消(布罗莫/外南梦)= 7/5 00:00 前 + 6/28 17:00 前

**3 晚不可取消 = 约 ¥900 一旦有变损失**,P23 风险预案要标红。

## 6. Cookie 拒收标准(BDUSS / BAIDUID / _xsrf)

**3 类 cookie 必须拒收**(2026-06-07 user 误贴 BDUSS,劝阻后撤):

| Cookie 类型 | 风险 | 处理 |
|---|---|---|
| **BDUSS_BFESS / PTA / BAIDUID** | 百度/阿里长期登录凭证(被劫持 = 网盘/支付/知道泄漏) | **拒收**,换公开源(AI_Go_Hotel / Booking) |
| **_xsrf / sessionid** | 短期会话(可换) | 可代用但写 turn 历史永久记录,**不替用户登录** |
| **ctrip 业务 cookie** | 携程 ToS 禁止自动化登录,触发风控 | 用 SPA e2e 抓取代替 |

**安全口径**:
1. 我能做的 = 公开源匿名(Booking / TripAdvisor / AI_Go_Hotel / Google Maps / amap)
2. 不能做 = 登录态抓取 / 验证码回填 / 用用户 cookie
3. 验证码 60s 失效,串行 turn 根本来不及,**强提示用户别发**
4. 携程 ToS 禁止自动化,触发风控 = 用户账号封禁 = 永久不能用

**回复模板**:

```
不能,而且请你不要发。
- 携程 API(soa2/14552 等)m.ctrip.com/restapi 11010 Forbidden = 已反爬
- 你给 cookie = 跨域用不上(BAIDUID_BFESS = 百度账号 = 我用 m.ctrip 拿不到数据)
- 验证码 60s 失效,turn-by-turn 必超
- 携程 ToS 禁止自动化,登录态抓 = 账号封禁

我做的:AI_Go_Hotel_MCP 公开(本次 5 家全拿到 hotelId + 真实房型+价)、
Booking.com 公开、TripAdvisor 公开、Google Maps 公开 — 全部匿名,完全够用。
```

## 7. 5 段 roomtoken 抓全脚本(模板)

```python
# 已知 1 段 roomtoken,改 SH + dates + segment 推其他 4 段
# 用户贴 URL 后,从 URL 抠出:
base = "02_H{hotelId}_R{roomId}_I{checkin}_O{checkout}_C{custId}_RatePlan{rp}_SP0_RP{price}_SH{hotelId}_SID0_SCtx_SPay_PTrue_Segment{seg}_BTPP_HR0_HBT_HP_STFalse_HC_F2Pfalse_PID_RateId021_ORP{price}_V{vid}"
# 5 段填 5 个不同 hotelId / dates / seg
```

实际**更省事的做法**:用户贴 URL → 我用 AI_Go_Hotel_MCP 用**英文酒店名**直接搜,**5 次 searchHotels 拿到 5 个 hotelId**(本次 p69762187 验证 5/5 成功,5-10s 拿全)。

## 8. 8 步工作流(更新)

1. e2e 抓产品 + **下载全量图(6 类)**
2. **M3 视觉读图**(主图 banner 提取完整文字 + 行程;POI 选 1-2 张真景点;hotel 看档次)
3. **图文日历 → 真实 5 家酒店**(不是 imageHotelList 9 家)
4. **AI_Go_Hotel_MCP 5 次 searchHotels → 5 个 hotelId**
5. 5 次 getHotelDetail 拿 7/4-10 当日房价
6. 拼 PPT P06(5 家真 + 价 + 距 + 不可取消标红)
7. 拼 P13-16 单日详情(每页 +1 真图)
8. 渲染 + 交付(8 步可执行清单见 [execution-checklist.md](execution-checklist.md))
