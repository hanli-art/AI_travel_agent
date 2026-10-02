from agents import Agent, function_tool
from config import model
from mcp_tools.schemas import TrainSearchParms, FlightSearchParms
from skill.traffic_skill import TrafficSkill


@function_tool
async def tool_search_train(params: TrainSearchParms) -> str:
    """查询两站之间的真实火车班次、时刻与票价（数据来自聚合数据/12306）。

    Args:
        params: 火车票查询入参。departure_station 出发站或城市名（如「杭州」「杭州东」）；
            arrival_station 到达站或城市名（如「福州」「福州南」）；date 出发日期
            YYYY-MM-DD（仅支持未来 15 天内）；train_filter 可选，车次类型如 G（高铁）、
            D（动车）；departure_time_range 可选，出发时段：凌晨/上午/下午/晚上。
    """
    result = await TrafficSkill.search_train(params)
    return result.model_dump_json(exclude_none=True)


@function_tool
async def tool_search_flight(params: FlightSearchParms) -> str:
    """查询两城之间的真实航班时刻与参考票价（数据来自聚合数据）。

    Args:
        params: 航班查询入参。departure_city 出发城市（如「杭州」，支持常见城市名或
            IATA 三字码如 HGH）；arrival_city 到达城市（如「北京」或 BJS）；
            date 出发日期 YYYY-MM-DD；direct_only 是否只看直飞。
    """
    result = await TrafficSkill.search_flight(params)
    return result.model_dump_json(exclude_none=True)


traffic_agent = Agent(
    name='traffic_agent',
    model=model,
    tools=[tool_search_train, tool_search_flight],
    instructions="""你是交通出行专家，负责城际火车票与机票查询。
1. 用户问火车/高铁/动车时，必须调用 tool_search_train 查真实班次；问飞机/航班时调用 tool_search_flight，不要凭空编造车次、航班号或票价。
2. 火车票工具需传出发站、到达站和日期（格式 YYYY-MM-DD，仅支持未来 15 天）；用户未说日期时，先询问或默认明天，超过 15 天的日期要提醒用户。
3. 航班工具需传出发城市、到达城市和日期；常见城市名会自动转 IATA 三字码，遇到不支持的城市请提示改用三字码。
4. 拿到数据后用中文整理输出：车次/航班号、出发与到达时刻、历时、票价或参考票价，并给出 2-3 个推荐方案与购票提醒。
5. 工具未返回结果时，如实说明可更换日期或站点/允许中转，不要编造。
6. 用户询问「从车站/机场到目的地怎么走」时，结合接驳建议回答。
7. 全程使用中文回答。"""
)