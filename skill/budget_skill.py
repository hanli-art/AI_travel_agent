from typing import List

from mcp_tools.schemas import (
    BudgetSearchParms,
    BudgetSearchOutput,
    BudgetBreakdownItem,
)

# 成本字段 → 中文费用项名
ITEM_LABELS = {
    "traffic_cost": "交通",
    "hotel_cost": "酒店",
    "food_cost": "美食",
    "tick_cost": "景点门票",
}


# 下面这个BudgetSkill类提供的方法会给budget_agent调用
class BudgetSkill:
    """预算计算：纯本地汇总，不调用任何外部接口"""

    @staticmethod
    async def calculate_budget(params: BudgetSearchParms) -> BudgetSearchOutput:
        """汇总各项成本，输出总预算、人均预算、日均预算与各项占比"""
        people = params.people or 1
        if people < 1:
            raise ValueError("出行人数必须大于 0")

        # 1. 逐项收集已提供的费用，未提供的记入缺失项（不按 0 计入，避免低估总预算）
        breakdown: List[BudgetBreakdownItem] = []
        missing: List[str] = []
        for field, label in ITEM_LABELS.items():
            cost = getattr(params, field)
            if cost is None:
                missing.append(label)
                continue
            breakdown.append(BudgetBreakdownItem(item_name=label, cost=cost, ratio=0.0))

        total = sum(item.cost for item in breakdown)
        # 2. 占比以总预算为分母（总预算为 0 时不计算，避免除零）
        for item in breakdown:
            item.ratio = round(item.cost / total, 4) if total else 0.0
        # 3. 明细按金额降序，便于看出主要开销
        breakdown.sort(key=lambda item: item.cost, reverse=True)

        daily = round(total / params.travel_days, 2) if params.travel_days else None
        return BudgetSearchOutput(
            total_cost=total,
            people=people,
            per_person_cost=round(total / people, 2),
            daily_average=daily,
            breakdown=breakdown,
            missing_items=missing,
            suggest=BudgetSkill.build_suggest(params, total, people, breakdown, missing),
        )

    @staticmethod
    def build_suggest(
        params: BudgetSearchParms,
        total: int,
        people: int,
        breakdown: List[BudgetBreakdownItem],
        missing: List[str],
    ) -> str:
        """生成预算总体建议（缺项时明确提示总预算可能被低估）"""
        if total == 0:
            return (
                "交通、酒店、美食、门票四项费用都未提供，暂时无法估算预算，"
                "请先告知其中至少一项的大致花费。"
            )
        parts = [f"总预算约 {total} 元，按 {people} 人计算人均约 {round(total / people, 2)} 元。"]
        if breakdown:
            top = breakdown[0]
            parts.append(f"其中{top.item_name}占比最高（{top.ratio * 100:.0f}%）。")
        if missing:
            parts.append(f"未提供{'、'.join(missing)}费用，实际总预算可能更高。")
        if params.travel_days:
            parts.append(f"按 {params.travel_days} 天估算，日均约 {round(total / params.travel_days, 2)} 元。")
        return "".join(parts)