from agents import Agent, function_tool
from config import model
from mcp_tools.schemas import BudgetSearchParms
from skill.budget_skill import BudgetSkill


@function_tool
async def tool_calculate_budget(params: BudgetSearchParms) -> str:
    """汇总交通/酒店/美食/门票成本，计算总预算、人均预算与各项占比。

    Args:
        params: 预算计算入参。traffic_cost 交通成本合计、hotel_cost 酒店成本合计、
            food_cost 美食成本合计、tick_cost 景点门票成本合计（单位均为元，未提供的项不传）；
            people 出行人数（默认 1，用于算人均）；travel_days 出行天数（可选，用于算日均）。
    """
    result = await BudgetSkill.calculate_budget(params)
    return result.model_dump_json(exclude_none=True)


budget_agent = Agent(
    name='budget_agent',
    model=model,
    tools=[tool_calculate_budget],
    instructions="""你是旅行预算分析师。
1. 用户询问旅行花费/预算时，必须调用 tool_calculate_budget 做汇总计算，不要凭空给出金额。
2. 从对话上下文（路线、交通、酒店、美食等子智能体的结果）中提取各项成本，能确定的才传入；
   无法确定的费用项不要编造也不要填 0，直接不传，工具会提示该项缺失。
3. 金额单位为元；人均 = 总预算 / 人数，人数未知时按 1 人计算并提醒用户。
4. 拿到结果后用中文输出：总预算、人均预算、各项费用与占比，并给出省钱建议。
5. 全程使用中文回答。"""
)