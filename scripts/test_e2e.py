"""test_e2e.py v2 - 详细错误 + 真实诊断"""
import sys, asyncio, json, traceback
sys.path.insert(0, '/opt/data/ctrip-mcp/src')

try:
    from ctrip_mcp.server import call_tool, app
except Exception as e:
    print(f"❌ 导入失败: {type(e).__name__}: {e}")
    print("\n[Debug] 看 sys.path:")
    for p in sys.path[:5]:
        print(f"  {p}")
    print("\n[Debug] 看 ctrip_mcp 是否在:")
    import os
    if os.path.exists('/opt/data/ctrip-mcp/src/ctrip_mcp'):
        print(f"  ✓ /opt/data/ctrip-mcp/src/ctrip_mcp 存在")
    else:
        print(f"  ✗ 不存在")
    sys.exit(1)

async def main():
    print("=== 1) ctrip_spa_capture ===")
    try:
        r1 = await call_tool("ctrip_spa_capture", {
            "product_id": 64158367,
            "depart_city_id": 2,
            "scroll": True,
        })
        if not r1:
            print("  ❌ 返回空 list!")
            return
        print(f"  返回数量: {len(r1)}")
        for i, c in enumerate(r1):
            text = c.text or ""
            print(f"  [{i}] type={c.type} text_len={len(text)}")
            if not text:
                print(f"  ❌ [{i}] text 为空!")
                continue
            # 解析
            try:
                d = json.loads(text)
                if 'duration_s' in d:
                    print(f"  ✓ duration: {d['duration_s']}s, xhrs: {len(d.get('xhrs', []))}")
                    for tag, path in d.get('saved', {}).items():
                        print(f"    saved {tag}: {path}")
                else:
                    print(f"  ⚠ text 是 JSON 但不带 duration_s: {text[:200]}")
            except json.JSONDecodeError as e:
                print(f"  ❌ JSON 解析失败: {e}")
                print(f"  text 前 200 字符: {text[:200]}")
                print(f"  text 后 200 字符: {text[-200:]}")
                return
    except Exception as e:
        print(f"  ❌ 调 call_tool 失败: {type(e).__name__}: {e}")
        traceback.print_exc()
        return

    print("\n=== 2) ctrip_get_product ===")
    r2 = await call_tool("ctrip_get_product", {"product_id": 64158367})
    if not r2 or not r2[0].text:
        print(f"  ❌ 返回空: {r2}")
        return
    try:
        d = json.loads(r2[0].text)
        if "❌" in r2[0].text or "错误" in r2[0].text:
            print(f"  ❌ tool 内部错: {r2[0].text[:500]}")
            return
        pb = d['product_basic']
        print(f"  ✓ name: {pb['name']}")
        print(f"  ✓ min_price: ¥{pb['min_price']}")
    except json.JSONDecodeError as e:
        print(f"  ❌ JSON 解析失败: {e}")
        print(f"  text: {r2[0].text[:300]}")
    except KeyError as e:
        print(f"  ⚠ 数据缺字段: {e}")
        print(f"  text 前 500: {r2[0].text[:500]}")


asyncio.run(main())
