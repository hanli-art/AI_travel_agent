from agents import Agent, function_tool
from config import model
from mcp_tools.schemas import FoodSearchParms
from skill.food_skill import FoodSkill


@function_tool
async def tool_search_food(params: FoodSearchParms) -> str:
    """根据城市与菜系搜索真实餐厅，返回餐厅名称、人均参考价、菜系、评分与地址。

    Args:
        params: 美食查询入参。city 目标城市（如「杭州」）；cuisine 可选，菜系或关键词
            （如「杭帮菜」「火锅」「日料」）；budget 可选，人均预算（元），只保留人均不超过该值的餐厅。
    """
    result = await FoodSkill.search_food(params)
    return result.model_dump_json(exclude_none=True)


food_agent = Agent(
    name='food_agent',
    model=model,
    tools=[tool_search_food],
    instructions="""你是美食推荐专家。
1. 用户询问某地美食/餐厅时，必须调用 tool_search_food 获取高德真实 POI 数据，不要凭空编造餐厅名或价格。
2. 用户给了菜系或口味（如「杭帮菜」「火锅」）时作为 cuisine 传入；给了人均预算时作为 budget 传入。
3. 高德多数餐厅不提供人均报价：工具返回的 price 为空时不要编造价格，统一说明「以实际消费为准」。
4. 拿到数据后用中文整理输出：餐厅名称、菜系、人均参考价、评分、地址，推荐 2-3 家不同选择的餐厅，并给出点餐或用餐建议。
5. 工具没返回结果时如实说明可更换菜系关键词或放宽预算，不要编造。
6. 全程使用中文回答。"""
)