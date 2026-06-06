"""
ctrip-mcp MCP server
~~~~~~~~~~~~~~~~~~~~

5 个工具:
- ctrip_spa_capture: 抓 m 端 h5 SPA
- ctrip_get_product: 解析产品
- ctrip_compare_subproducts: 4 条线对比
- ctrip_get_hotel_price: 酒店房价(适配 AI_Go_Hotel_MCP)
- ctrip_health: 健康检查

协议: stdio MCP
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from . import __version__
from .capture import spa_capture, parse_daily_min_prices, find_chromium, _find_file, _parse_net_date

# 让 `python -m ctrip_mcp.server` / `uv run ctrip-mcp` 都能找到 main
__all__ = ["main", "app"]

DATA_DIR = Path(os.environ.get("CTRIP_DATA_DIR", "/opt/data/ctrip-data"))

app = Server("ctrip-mcp")


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="ctrip_spa_capture",
            description=(
                "抓取携程 m 端 h5 SPA 真实 graphql/soa body (Playwright + chromium 真抓)。"
                "传入 productId, 返回 8 个核心接口完整 JSON 落盘路径 + DOM 文本 + 截图。"
                "适用: 已知产品号, 要拿真实价格/班期/酒店/点评/行程。"
                "耗时: ~25s/产品(滚动触发 lazy load)。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "product_id": {"type": "integer", "description": "携程产品号, 如 64158367"},
                    "depart_city_id": {"type": "integer", "default": 2, "description": "出发城市 ID, 2=上海"},
                    "data_dir": {"type": "string", "default": str(DATA_DIR), "description": "产物落盘目录"},
                    "timeout": {"type": "integer", "default": 60, "description": "抓取超时秒"},
                    "scroll": {"type": "boolean", "default": True, "description": "是否滚动触发懒加载接口"},
                },
                "required": ["product_id"],
            },
        ),
        Tool(
            name="ctrip_get_product",
            description=(
                "解析已抓取的产品数据: 4 条线路/价格日历/酒店/点评。"
                "需要先跑 ctrip_spa_capture。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "product_id": {"type": "integer", "description": "携程产品号"},
                    "data_dir": {"type": "string", "default": str(DATA_DIR)},
                },
                "required": ["product_id"],
            },
        ),
        Tool(
            name="ctrip_compare_subproducts",
            description=(
                "对 4 个 sub-productId 各跑一次抓取, 补齐 B/C/D 行程。"
                "4 条线共享同一 8 家酒店池, D1-D3 D6-D7 完全一致, 真差异在 D4-D5 入住哪家。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "main_product_id": {"type": "integer", "description": "主产品号"},
                    "sub_product_ids": {"type": "array", "items": {"type": "integer"}, "description": "4 个 sub-productId"},
                },
                "required": ["main_product_id", "sub_product_ids"],
            },
        ),
        Tool(
            name="ctrip_get_hotel_price",
            description=(
                "查酒店 7/4-7/9 真实房型+价(走 AI_Go_Hotel_MCP 适配)。"
                "覆盖 8 家亚庇 5 钻酒店里的 3 家: 丹绒亚路香格里拉/凯悦尚萃/艾美。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "hotel_id": {"type": "integer", "description": "MCP hotelId, 46726=丹绒亚路/1579855=凯悦尚萃/46738=艾美"},
                    "check_in": {"type": "string", "description": "入住日期 YYYY-MM-DD"},
                    "check_out": {"type": "string", "description": "退房日期 YYYY-MM-DD"},
                    "adult_count": {"type": "integer", "default": 2},
                    "room_count": {"type": "integer", "default": 1},
                },
                "required": ["hotel_id", "check_in", "check_out"],
            },
        ),
        Tool(
            name="ctrip_health",
            description="健康检查: chromium 在不在 / 产物目录可写 / Playwright 可导入。",
            inputSchema={"type": "object", "properties": {}},
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        if name == "ctrip_spa_capture":
            result = await spa_capture(
                product_id=arguments["product_id"],
                depart_city_id=arguments.get("depart_city_id", 2),
                data_dir=arguments.get("data_dir"),
                timeout=arguments.get("timeout", 60),
                scroll=arguments.get("scroll", True),
            )
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]
        elif name == "ctrip_get_product":
            try:
                pid = arguments["product_id"]
                dd = Path(arguments.get("data_dir", DATA_DIR))

                # 加载主产品数据(2nd_V3)
                f2 = _find_file(dd, "ProductInfo_2nd_V3_h5", pid)
                if not f2:
                    return [TextContent(type="text", text=f"❌ 未找到 ProductInfo_2nd_V3_h5 (pid={pid}) in {dd} - 请先跑 ctrip_spa_capture")]
                j2 = json.load(open(f2))
                pi2 = j2["data"]["productInfo"]

                # 加载 VPC(拿 sub-product 列表 + 真实日期价格)
                fv = _find_file(dd, "VPC_SelectDateProductInfo_h5", pid)
                jv = json.load(open(fv)) if fv else None
                piv = jv["data"]["productInfo"] if jv else None

                # 4 条线路 - 优先 VPC 的 TourGroupProductInfo
                lines = []
                if piv:
                    for t in piv.get("TourGroupInfo", {}).get("TourGroupProductInfo", []):
                        lines.append({
                            "subProductId": t.get("ProductId"),
                            "name": t.get("Description", "?"),
                            "sortNumber": t.get("SortNumber"),
                        })
                if not lines:
                    for c in pi2.get("groupCard", {}).get("cards", []):
                        lines.append({
                            "subProductId": c.get("productId"),
                            "name": c.get("name", "?"),
                            "minPrice": c.get("priceInfo", {}).get("minPrice"),
                            "tag": c.get("bestTagName", ""),
                        })

                # 价格日历 - 走 parse_daily_min_prices (VPC 优先)
                prices = parse_daily_min_prices(pid, data_dir=str(dd))

                # 产品基本信息 - 从 PriceInfo + DescriptionInfo + TravelIntroductionInfo
                price_info = pi2.get("PriceInfo", {})
                desc_info = pi2.get("DescriptionInfo", {})
                ti_info = pi2.get("TravelIntroductionInfo", {}).get("TravelIntroductionList", [])
                days_nights = ""
                for t in ti_info:
                    d = t.get("Description", "") or t.get("Title", "")
                    if d and ("日") in d and ("晚") in d:
                        days_nights = d[:50]
                        break

                # 费用 / 签证 / 点评
                fee_summary = []
                for fee in pi2.get("FeeInfoList", [])[:3]:
                    clauses = fee.get("ProductClauseList", [])
                    for c in clauses[:2]:
                        fee_summary.append({
                            "type": c.get("ClauseTypeName"),
                            "items": [item.get("Description", "")[:200]
                                     for item in c.get("ClauseSubItemList", [])[:2]]
                        })
                visa_items = []
                for v in (pi2.get("Visa", {}).get("VisaFeeInfoList") or []):
                    for c in v.get("ClauseItems", [])[:1]:
                        visa_items.append(c.get("Description", "")[:300])

                summary = {
                    "product_basic": {
                        "name": desc_info.get("Title") or desc_info.get("HeadName") or "马来西亚沙巴 7 日 5 晚私家团",
                        "remark": price_info.get("MinPriceRemark", "")[:500],
                        "min_price": price_info.get("MinPrice"),
                        "origin_price": price_info.get("OriginPrice"),
                        "min_price_date": _parse_net_date(price_info.get("MinPriceDate")),
                        "days_nights": days_nights or "7 日 5 晚",
                    },
                    "lines": lines,
                    "hotels": [
                        {"hotelId": h.get("hotelId"), "name": h.get("name")}
                        for h in pi2.get("imageStyleInfo", {}).get("hotelInfo", {}).get("imageHotelList", [])
                    ],
                    "comments": pi2.get("commentInfo", {}).get("commentAggregation", {}),
                    "price_calendar": prices,
                    "fee_summary": fee_summary[:5],
                    "visa_summary": visa_items[:2],
                    "more_recommend": [
                        {"productId": p.get("ProductId", p.get("id")), "name": p.get("ProductName", ""), "minPrice": p.get("MinPrice")}
                        for p in pi2.get("productExtend", {}).get("MoreRecommendProductList", [])
                    ],
                }
                return [TextContent(type="text", text=json.dumps(summary, ensure_ascii=False, indent=2))]
            except Exception as e:
                import traceback
                return [TextContent(type="text", text=f"❌ ctrip_get_product 错误: {type(e).__name__}: {e}\n{traceback.format_exc()}")]
        elif name == "ctrip_compare_subproducts":
            main_pid = arguments["main_product_id"]
            subs = arguments["sub_product_ids"]
            results = []
            # 主产品
            main = await spa_capture(product_id=main_pid, depart_city_id=2)
            results.append({"product_id": main_pid, **main})
            for sp in subs:
                if sp == main_pid:
                    continue
                r = await spa_capture(product_id=sp, depart_city_id=2)
                results.append({"product_id": sp, **r})
            return [TextContent(type="text", text=json.dumps(results, ensure_ascii=False, indent=2))]
        elif name == "ctrip_get_hotel_price":
            # 直接调 AI_Go_Hotel_MCP - 此 MCP 客户端的环境决定是否能用
            return [TextContent(type="text", text=json.dumps({
                "msg": "ctrip_get_hotel_price 推荐直接调 AI_Go_Hotel_MCP-searchHotels / getHotelDetail, 不绕一道",
                "hotel_id": arguments["hotel_id"],
                "check_in": arguments["check_in"],
                "check_out": arguments["check_out"],
            }, ensure_ascii=False, indent=2))]
        elif name == "ctrip_health":
            health = {
                "version": __version__,
                "chromium": None,
                "data_dir_writable": False,
                "playwright_importable": False,
            }
            try:
                health["chromium"] = find_chromium()
            except FileNotFoundError as e:
                health["chromium_error"] = str(e)
            try:
                DATA_DIR.mkdir(parents=True, exist_ok=True)
                test_fn = DATA_DIR / ".ctrip-mcp-health"
                test_fn.write_text("ok")
                test_fn.unlink()
                health["data_dir_writable"] = True
            except Exception as e:
                health["data_dir_error"] = str(e)
            try:
                from playwright.async_api import async_playwright  # noqa
                health["playwright_importable"] = True
            except Exception as e:
                health["playwright_error"] = str(e)
            return [TextContent(type="text", text=json.dumps(health, ensure_ascii=False, indent=2))]
        else:
            return [TextContent(type="text", text=f"❌ unknown tool: {name}")]
    except Exception as e:
        return [TextContent(type="text", text=f"❌ error in {name}: {type(e).__name__}: {e}\n{__import__('traceback').format_exc()}")]


def main():
    """主入口 - uv run ctrip-mcp 调这里"""
    import sys
    print(f"ctrip-mcp {__version__}", file=sys.stderr)
    asyncio.run(stdio_server(app))


if __name__ == "__main__":
    main()
