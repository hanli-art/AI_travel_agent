"""P8 验收：验证预算汇总（纯计算，不调用外部接口）。"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_tools.schemas import BudgetSearchParms
from skill.budget_skill import BudgetSkill


async def main():
    # 场景 1：四项费用齐全，2 人 4 天
    params = BudgetSearchParms(
        traffic_cost=1200,
        hotel_cost=1600,
        food_cost=900,
        tick_cost=500,
        people=2,
        travel_days=4,
    )
    out = await BudgetSkill.calculate_budget(params)
    print("=" * 60)
    print(
        f"[预算] 总预算={out.total_cost}元 | 人数={out.people} | "
        f"人均={out.per_person_cost}元 | 日均={out.daily_average}元"
    )
    for item in out.breakdown:
        print(f"  {item.item_name} | {item.cost}元 | 占比{item.ratio * 100:.1f}%")
    print("[缺失项]", out.missing_items)
    print("[建议]", out.suggest)
    print("=" * 60)

    # 场景 2：只提供部分费用、人数未知（验证缺项提示与人均兜底）
    part = BudgetSearchParms(traffic_cost=800, hotel_cost=1200)
    out2 = await BudgetSkill.calculate_budget(part)
    print(
        f"[部分费用] 总预算={out2.total_cost}元 | 人数={out2.people} | "
        f"人均={out2.per_person_cost}元 | 缺失={out2.missing_items}"
    )
    print("[建议]", out2.suggest)
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())