"""P3 验收：走真实 RoutePlanMCP.execute() 路径，检查 5 个问题的修复情况。"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_tools.amap_mcp import RoutePlanMCP
from mcp_tools.schemas import RoutePlanParms


async def main():
    params = RoutePlanParms(
        startCity="福州",
        origin_address="福州飞南路86号",
        endCity="杭州",
        dest_address="雷峰塔",
        travel_mode="自驾",
        travel_days=6,
        preference="速度优先",
    )
    route = await RoutePlanMCP().execute(params)

    print("=" * 60)
    print("origin        :", route.origin)
    print("destination   :", route.destination)
    print("pass_cities   :", route.pass_cities)
    print("total_distance:", route.total_distance_km, "km")
    print("total_hours   :", route.total_drive_hours, "h")
    print("total_toll    :", route.total_toll_fee, "元")
    print("route_strategy:", route.route_strategy)
    print("has_mountain  :", route.has_mountain_road)
    print("global_tips   :", route.global_tips)
    print("-" * 60)
    print(f"daily_segments: {len(route.daily_segments)} 段")
    for i, seg in enumerate(route.daily_segments, 1):
        spots = [s.spot_name for s in seg.scenic_spots]
        print(
            f"  [{i:2d}] {seg.section_name:<28} {seg.distance_km:>4}km "
            f"{seg.drive_hours:>5}h  {seg.road_type:<6} 服务:{seg.service_info} 景点:{spots}"
        )
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
