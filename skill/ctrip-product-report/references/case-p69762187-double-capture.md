# Case: p69762187(印尼私家团) vs p42461732(印尼 7 日 6 晚) — 三大教训

> 抓取时间: 2026-06-06 21:38 (p69762187) + 2026-06-06 20:58 (p42461732)
> 数据目录: /opt/data/ctrip-data/

## 教训 1: **必须双跑 2nd_V3 + VPC**(致命遗漏)

p42461732 只跑了 2nd_V3, **漏了 12 个关键字段**。p69762187 跑全了发现 VPC 才是数据金矿。

### VPC 独有的 12 个字段(2nd_V3 全部缺失)

| 字段 | VPC 路径 | 报告用法 | p69762187 真实值示例 |
|---|---|---|---|
| **完整产品名** | `BasicInfo.MainName/SubName` | 报告标题/产品名 | "印度尼西亚巴厘岛+泗水+布罗莫火山+佩妮达岛7日6晚私家团" |
| **行程 10 段结构** | `SegmentInfo.Segments[]` | **D1-D7 真实结构** (不靠 DOM) | 10 段: 上海→泗水→Kanigaran→Licin→巴厘岛→上海 |
| **目的地层级** | `BasicInfo.Destinations[]` | 报告"目的地"段 | 13 项: 1 国 + 2 省 + 10 城 |
| **班期规则** | `SegmentInfo.Segments[].Schedule` | "每天发" / "周末发" | "1234567" (每天) |
| **多城市价** | `PriceInfo.DepartureCityPriceList` | 报告"出发城市价" | **68 城市**(上海 7557 / 深圳 6345 / 广州 7901) |
| **销量** | `BasicInfo.OrderPersonCount` / `PersonsMonth` | 报告"销量" | 328 / 6 |
| **流量** | `BasicInfo.VacationPersons` | 报告"热度" | 月访问 8636 / 周 2082 / 月咨询 357 |
| **年龄段** | `BasicExtendInfo.PriceStandardList` | 报告"儿童价/年龄" | 12+ 算成人 / 2-12 算儿童 |
| **服务语言** | `BasicExtendInfo.ServiceLanguages` | 报告"中文服务" | 普通话 |
| **截单时间** | `BasicInfo.BookingTime` | 报告"最晚下单" | 出发前 1 天 18:00 |
| **供应商信息** | `VendorInfo` | 报告"合同方 / 客服" | 携程自营 (BC: 913101107390065156) / 4008663333 / 24h |
| **行程核心** | `BasicInfo.CorePoiTitle` | 报告"核心景点" | "爪哇岛·KapasBiruWaterfall·罗威纳海滩·德格拉朗梯田·佩妮达岛" |

### 改 spa_capture 抓取策略(必加)

```bash
# 现在: 只跑 2nd_V3
/opt/hermes/.venv/bin/python /opt/data/skills/devops/ctrip-spa-capture/scripts/ctrip_spa_capture.py 64158367 2

# 改后: 跑 2nd_V3 + 强制多抓 VPC
/opt/hermes/.venv/bin/python /opt/data/skills/devops/ctrip-spa-capture/scripts/ctrip_spa_capture.py 64158367 2 --include-vpc
# 或默认行为改为必跑 VPC
```

**判断条件**: `VPC_SelectDateProductInfo_h5.json` 文件存在且 > 100KB = VPC 已抓;否则补抓。

### 改 ctrip-mcp 的 `ctrip_spa_capture` 工具(必加)

工具参数加 `include_vpc: bool = True` 默认开,返回结果说明"双跑完成"还是"只跑了 2nd_V3"。

---

## 教训 2: **cardItems(7 大类) vs TravelSummaryModuleList(14 模块) 模板自适应**

**两个产品用了不同前端模板**:

| 模板 | 出现产品 | 路径 | 数据 |
|---|---|---|---|
| **A: cardItems (7 大类)** | p69762187 | `groupCard.cards[0].cardItems[]` | 行/住/团/游/导/餐/活 (7 段简洁) |
| **B: TravelSummaryModuleList** | p42461732 | `TravelIntroductionInfo.TravelIntroductionList[0].TravelOverviewInfo.TravelSummaryModuleList[]` | 14 模块结构化(住宿/购物/餐食/接送机/服务语言/团友说明/年龄限制/...) |

### 自适应代码模板

```python
def extract_7_categories(pi):
    """适配两种模板,统一返回 7 大类"""
    result = {'行': '?', '住': '?', '团': '?', '游': '?', '导': '?', '餐': '?', '活': '?'}
    
    # 模板 A: cardItems
    card_items = pi.get('groupCard', {}).get('cards', [{}])[0].get('cardItems', [])
    if card_items:
        for ci in card_items:
            name = ci.get('groupName', '?')
            content = ci.get('displayContent', '?')
            if not ci.get('isHidden', True) and content and content != '暂无信息':
                result[name] = content
        return result
    
    # 模板 B: TravelSummaryModuleList (映射到 7 大类)
    til = pi.get('TravelIntroductionInfo', {}).get('TravelIntroductionList', [{}])
    if til:
        modules = {m['ModuleName']: m.get('Description', '') 
                   for m in til[0].get('TravelOverviewInfo', {}).get('TravelSummaryModuleList', [])}
        # 14 模块 → 7 大类映射
        result['行'] = modules.get('往返交通', '?')
        result['住'] = modules.get('住宿', '?')
        result['团'] = modules.get('团队人数', '?') or modules.get('团友说明', '?')
        result['游'] = f"{til[0].get('TravelOverviewInfo', {}).get('ScenicTimes', '?')} 个景点"
        result['导'] = modules.get('是否有导游', '?')
        result['餐'] = modules.get('餐食', '?')
        result['活'] = modules.get('自由活动', '?')
        return result
    
    return result
```

**为什么必须自适应**: p69762187 走 cardItems(7 段简洁,产品页"行/住/团/游/导/餐/活"直接展示), p42461732 走 TravelSummaryModuleList(14 模块更细,但产品页"行程亮点"展示)。**报告里"产品亮点"段不能固定写 cardItems 路径**。

---

## 教训 3: **FeeInfoList 真实字段是 `TargetPopulationItemList`,不是 `Description`**

**反复踩坑(2026-06-06 验证)**: `ClauseSubItemList[].Description` 字段在 2nd_V3 里**不存在**。真实数据是:

```python
# ❌ 错误: 期望 Description 字段
for sub in cl['ClauseSubItemList']:
    desc = sub.get('Description', '?')  # 总是 "?"

# ✅ 正确: 走 TargetPopulationItemList (按人群)
for sub in cl['ClauseSubItemList']:
    for tp in sub.get('TargetPopulationItemList', []):
        tp_name = tp.get('TargetPopulationName', '?')  # '成人' / '儿童' / '?'(未指定)
        desc = tp.get('Description', '')
        if desc:
            print(f"[{sub.get('SubTitle')}] ({tp_name}): {desc}")
```

p69762187 实测拿到的真实费用含/不含:

| 类别 | 子类 | 内容 |
|---|---|---|
| 费用包含 | 交通 | 去程上海→泗水机票(含税) + 返程巴厘岛→上海机票(含税) + 当地专车 7 天 |
| 费用包含 | 住宿 | 自选酒店 |
| 费用包含 | 餐食 | 成人 6 早 1 午 / 儿童 1 午 |
| 费用包含 | 随团服务 | 当地英语司机(仅接待, 不讲解景区) |
| 费用包含 | 门票 | 行程中首道大门票 |
| 费用包含 | 接送 | 行程首末日专车接送机 |
| **自理费用** | **税费** | **2024/2/14 起抵巴厘岛 15 万印尼盾/人(约 ¥70)旅游税** |
| 自理费用 | 签证/签注 | 本产品不含签证(落地签 35 美金/人现场付,约 ¥250) |
| 自理费用 | 其他 | 个人消费等 |

**报告必加"实际预算 = 起价 × 2 + 自理费用"段**,不能漏税费和签证。

---

## 教训 4: **天气数据真实降级链**

p69762187 沙巴 vs 印尼 7 日 6 晚案例, 用户问"天气怎么办", 测试了 3 个 mcphub 真实 MCP:

| MCP | 状态 | 限制 |
|---|---|---|
| `amap-mcp-maps_weather` | ✅ 通了 | **只覆盖中国**(泗水查询返"泗水县"错配, 登巴萨/巴厘岛/巴厘 NULL), **7 天外拿不到**(只给 4 天) |
| `weather-get_weather_forecast` | ❌ 404 OAuth | mcphub 鉴权配错, `Invalid session id` |
| `variflight-mcp-getFutureWeatherByAirport` | ❌ 404 OAuth | 同样鉴权问题 |

**真实降级链(2026-06-06 实测)**:

```
1. amap-mcp-maps_weather (国内, 7 天内)
   ↓ 失败/超期
2. variflight-mcp-getFutureWeatherByAirport (机场, 3 天内, 需要 OAuth 修)
   ↓ 失败
3. wendao-skill (LLM 复述, 7 天+, ⚠️ 知识截止 2026-01 + 串台风险)
   ↓ 失败
4. 历史均值(气候数据, 7 天+, 手工查 climate-data.org)
```

**报告天气段标准模板**:

> **天气对照**(2026-06-06 抓取时刻)
> | 日期 | 上海 | 泗水 | 巴厘岛 | 出海建议 |
> |---|---|---|---|---|
> | 6/6 | 高德 26°C 小雨 | 高德 26°C 小雨 | NULL(高德未覆盖印尼) | 泗水有雨, 巴厘岛查不到 |
> | 6/7 | 高德 24°C 阴 | 高德 24°C 阴 | NULL | - |
> | **7/4** | **wendao 预测 28-32°C 多云** | **wendao 预测 26-30°C 晴** | **wendao 预测 25-29°C 晴** | **wendao 知识截止 2026-01, 仅供方向参考, 以出行前 7 天高德实时为准** |
> | 7/5-7/10 | wendao 预测 | wendao 预测 | wendao 预测 | (同风险提示) |

---

## 教训 5: **wendao 实际表现(2026-06-06 实测)**

- **沙巴 case**: 短 query 串台, 给的不是 p64158367 而是 p71068823(产品号完全不同)
- **印尼 case**: 短 query 返"沙巴"产品,跟查询无关
- 知识截止 2026-01, 7/4 28 天后**完全是 LLM 推测**, 方向准但温度/降雨概率**会偏 1-3°C**

**wendao 安全使用姿势**:
1. **永远走金矿字段交叉验证**(`getCommentSummary` / `PriceInfo` / `MinPriceRemark`)
2. **报告"点评"段只放 wendao 摘要, 加"以携程 APP 实时为准"**
3. **7 天外的天气段必须标"LLM 预测, 仅供方向参考"**

---

## p69762187 报告输出要素清单(对照 SKILL.md 11 段)

| 段 | 字段 | 状态 |
|---|---|---|
| 1. 逐日行程 | `SegmentInfo.Segments` (10 段) | ✅ |
| 2. 酒店对比 | `imageStyleInfo.hotelInfo.imageHotelList` (9 家有 hotelId) | ✅ |
| 3. 航班 | `MinPriceRemark` 提到 CX365/CX629/CX782/CX316 | ✅ |
| 4. 费用明细 | `FeeInfoList` (9 项) | ✅ |
| 5. 优缺点 | 综合判断 | ✅ |
| 6. 天气对照 | 高德 + wendao 降级 | ✅ |
| 7. 目的地要事 | 巴厘岛旅游税 + 落地签 + 防晒 + 货币 | ✅ |
| 8. 产品经理说 | `PMRecomendInfo.RecommendList` 3 条 | ✅ |
| 9. 社区攻略 | `expertInfo.datas` 0 条攻略(只有点评 7 条) | ⚠️ 比 p42461732 少 |
| 10. 同类比价 | `MoreRecommendProductList` 8 个 (¥6412-¥10486) | ✅ |
| 11. 品牌背书 | 携程自营 + 328 人已购 + 月访问 8636 + 携程 24h 客服 | ✅ |

**额外加的 5 段金矿**(p69762187 才有):
- 7 大类 cardItems(模板 A)
- 13 个目的地层级
- 10 段 SegmentInfo 行程
- 68 城市价表
- 2 大必加费用(巴厘岛旅游税 + 落地签)

---

## p69762187 vs p42461732 字段差异表(写报告必查)

| 字段 | p42461732 | p69762187 | 报告用法 |
|---|---|---|---|
| **行程结构** | 靠 DOM 抽 D1-D7 | **VPC SegmentInfo 10 段** | 优先 VPC |
| **酒店列表** | 5 家(无 hotelId) | **9 家(有 hotelId)** | 优先 imageHotelList |
| **POI 列表** | 9 个(无 poiId) | **8 个(有 poiId)** | 优先 imageStyleInfo |
| **年龄段** | 缺 | **VPC PriceStandardList** | 报告"儿童价"段 |
| **销量/流量** | 缺 | **VPC BasicInfo.VacationPersons** | 报告"热度"段 |
| **多城市价** | 缺 | **VPC DepartureCityPriceList 68 城市** | 报告"出发城市价"段 |
| **目的地层级** | 缺 | **VPC Destinations 13 项** | 报告"目的地"段 |
| **班期规则** | 缺 | **VPC Segments[].Schedule** | 报告"班期"段 |
| **截单时间** | 缺 | **VPC BookingTime** | 报告"截单"段 |
| **供应商** | 缺 | **VPC VendorInfo** | 报告"客服/合同方"段 |
| **行程亮点模板** | 14 模块 | **7 大类 cardItems** | 自适应(见教训 2) |
| **套餐** | 限时促销 -¥57 + 套餐 -¥492 = -¥549 | 无 | 报告"促销"段 |
| **点评** | 5.0/2 详细 | 1 条文本 (没详细评分) | 标"评分以携程 APP 实时为准" |
| **目的地税费** | 缺 | **2024/2/14 起 15 万印尼盾旅游税/人** | 报告"实际预算"段 |
| **落地签** | 缺 | **35 美金/人** | 报告"实际预算"段 |

**结论**:**p69762187 用的前端模板(模板 A)字段比 p42461732(模板 B)更细**。报告生成时**必须优先走 VPC, 模板自适应(A/B 二选一)**。
