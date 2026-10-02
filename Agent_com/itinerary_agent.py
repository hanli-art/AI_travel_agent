from agents import Agent, function_tool
from config import model
from mcp_tools.itinerarySchemas import ItineraryParms
from skill.itinerary_skill import ItinerarySkill


@function_tool
async def tool_plan_itinerary(params: ItineraryParms) -> str:
    """按「出发地→目的地 + N 天」编排完整多日行程，返回逐日计划与预算。

    工具会依次串联路线规划、天气、酒店、美食与预算计算，逐日给出：
    路线分段、沿途景点、天气、住宿、餐饮推荐及当日费用估算。

    Args:
        params: 行程编排入参。start_city 出发城市、end_city 目的地城市、
            travel_days 行程天数（6天5夜传 6）；travel_mode 出行方式（默认驾车）；
            people 出行人数；start_date 出发日期 YYYY-MM-DD（可选，用于匹配天气预报）；
            hotel_price_max 每晚酒店预算上限（可选）；food_cuisine 餐饮偏好（可选）。
    """
    result = await ItinerarySkill.plan_itinerary(params)
    return result.model_dump_json(exclude_none=True)


itinerary_agent = Agent(
    name='itinerary_agent',
    model=model,
    tools=[tool_plan_itinerary],
    instructions="""你是多日行程编排专家，负责把路线、天气、酒店、美食、预算串成可执行的逐日计划。
1. 用户提出「从A到B N天N夜」这类多日行程需求时，必须调用 tool_plan_itinerary，不要凭空编排。
2. 从用户话里提取：出发城市、目的地城市、天数（6天5夜 → travel_days=6）、人数、出行方式、出发日期、酒店预算上限、餐饮偏好；未提到的不要编造。
3. 拿到结果后用中文输出 Markdown 逐日行程，每天都包含：路线分段（区间、里程、驾驶时长）、沿途景点（含门票与评分）、天气、住宿（名称/参考价/评分）、餐饮推荐（名称/人均）、当日费用估算。
4. 最后给出全程汇总：总里程、总驾驶时长、过路费与总预算/人均预算。工具返回的 notes 是数据缺失与估算口径说明，必须在回答里如实转述（例如油价估算口径、某天未获取报价）。
5. 工具返回的 price 为空时不要编造价格，统一说明「以实际预订/消费为准」。
6. 全程使用中文回答。"""
)