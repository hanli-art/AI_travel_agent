from agents import Agent, function_tool
from config import model
from mcp_tools.schemas import HotleSearchParms
from skill.hotel_skill import HotelSkill


@function_tool
async def tool_search_hotel(params: HotleSearchParms) -> str:
    """根据城市与地址搜索周边真实酒店，返回酒店名称、地址、参考价、评分与距离。

    Args:
        params: 酒店查询入参。city 目标城市；address 可选，景区/市中心等参考点
            （如「西湖」「大理古城」）；price_min/price_max 可选，价格区间（元/晚）；
            stay_days 可选，入住天数；crowd 可选，入住人群（如学生、教师）。
    """
    result = await HotelSkill.search_hotel(params)
    return result.model_dump_json(exclude_none=True)


hotel_agent = Agent(
    name='hotel_agent',
    model=model,
    tools=[tool_search_hotel],
    instructions="""你是酒店住宿推荐专家。
1. 用户询问某地酒店/住宿时，必须调用 tool_search_hotel 获取高德真实 POI 数据，不要凭空编造酒店名或价格。
2. 用户给了景区或具体地址（如「西湖」「大理古城」）时，把它作为 address 传入以便就近搜索；只给城市则只传 city。
3. 高德多数酒店不提供挂牌价：工具返回的 price 为空时不要编造价格，统一说明「以实际预订为准」。
4. 拿到数据后用中文整理输出：酒店名称、地址、参考价、评分、距参考点的距离，推荐 2-3 家不同档次的酒店，并给出入住建议。
5. 全程使用中文回答。"""
)