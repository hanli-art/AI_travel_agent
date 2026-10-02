from agents import Agent, function_tool
from config import model
from mcp_tools.schemas import RoutePlanParms
from skill.route_skill import RouteSkill


@function_tool
async def tool_plan_city_route(params: RoutePlanParms) -> str:
    """根据出发城市、目的城市、出行方式、天数、路线偏好规划自驾路线，返回真实的高德路线数据。

    Args:
        params: 路线规划入参，包含出发城市 startCity、目的城市 endCity、详细地址、
            出行方式 travel_mode、出行天数 travel_days、路线偏好 preference
            （高德策略编码：0 速度优先、1 费用优先、2 距离优先、3 不走高速）
    """
    route = await RouteSkill.plan_city_route(params)
    return route.model_dump_json()


route_agent = Agent(
    name='route_planning_agent',
    model=model,
    tools=[tool_plan_city_route],  # 👈 调用 skill 层，skill 层再去调 mcp 层
    instructions="""你是自驾游路线规划专家。
1. 用户给出出发地和目的地时，必须调用 tool_plan_city_route 获取真实路线数据，不要凭空编造路线。
2. 工具返回的是清洗后的分段行程数据，请基于它整理成清晰的中文行程建议：总里程、总驾驶时长、过路费、途经城市、分段道路类型、沿途景点，以及山路/隧道/限行等出行提示。
3. 缺少出发地或目的地时，先向用户确认再调用工具。
4. 全程使用中文回答。"""
)