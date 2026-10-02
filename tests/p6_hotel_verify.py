"""P6 验收：走真实 HotelSkill 路径，验证周边酒店搜索返回名称/地址/价格/评分。"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_tools.schemas import HotleSearchParms
from skill.hotel_skill import HotelSkill


async def main():
    params = HotleSearchParms(city="杭州", address="西湖", price_min=300, price_max=800, stay_days=2)
    out = await HotelSkill.search_hotel(params)
    print("=" * 50)
    print(f"[周边酒店] city={out.city} | 命中 {len(out.recommend_hotels)} 家")
    for h in out.recommend_hotels:
        print(
            f"  {h.hotel_name} | 参考价={h.price}元 | 评分={h.score} | "
            f"距离={h.distance_m}m | {h.address}"
        )
    print("[建议]", out.total_suggest)
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())