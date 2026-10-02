"""P7 验收：走真实 FoodSkill 路径，验证餐饮搜索返回名称/人均/菜系/评分/地址。"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_tools.schemas import FoodSearchParms
from skill.food_skill import FoodSkill


async def main():
    params = FoodSearchParms(city="杭州", cuisine="杭帮菜", budget=100)
    out = await FoodSkill.search_food(params)
    print("=" * 60)
    print(
        f"[美食] city={out.city} | cuisine={out.cuisine} | "
        f"命中 {len(out.recommend_foods)} 家"
    )
    for f in out.recommend_foods:
        price = f"{f.price}元" if f.price is not None else "价格需实际确认"
        print(
            f"  {f.food_name} | 菜系={f.cuisine} | 人均={price} | "
            f"评分={f.score} | {f.address}"
        )
    print("[建议]", out.total_suggest)
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())