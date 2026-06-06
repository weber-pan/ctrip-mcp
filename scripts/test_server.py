"""test ctrip-mcp server import + tool listing + health check"""
import sys, asyncio, json
sys.path.insert(0, '/opt/data/ctrip-mcp/src')

from ctrip_mcp.server import call_tool, list_tools
from mcp.types import TextContent

async def main():
    tools = await list_tools()
    print(f"Tools count: {len(tools)}")
    for t in tools:
        print(f"  - {t.name}")
    result = await call_tool("ctrip_health", {})
    for c in result:
        print("HEALTH:", c.text[:500])

asyncio.run(main())
