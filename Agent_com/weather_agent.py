from agents import Agent, function_tool
from config import model
from skill.weather_skill import WeatherSkill


@function_tool
async def tool_query_weather(city: str, address: str = "", extensions: str = "base") -> str:
    """查询指定城市的实时天气或未来几天天气预报，返回高德真实天气数据。

    Args:
        city: 城市名，如「杭州」「大理」「福州」
        address: 可选，具体地址或景点，如「雷峰塔」，用于定位到区县
        extensions: base=实时天气（默认）；all=未来3天预报
    """
    resp = await WeatherSkill.query_weather(city, address, extensions)
    return resp.model_dump_json(exclude_none=True)


weather_agent = Agent(
    name='weather_agent',
    model=model,
    tools=[tool_query_weather],
    instructions="""你是天气查询专家。
1. 用户询问某地天气时，必须调用 tool_query_weather 获取高德真实天气数据，不要凭空编造。
2. 问「现在天气/实时天气」用 extensions=base；问「未来几天/明天/预报」用 extensions=all。
3. 用户只给城市时 city 传城市名即可；给了具体景点或地址时一并传入 address。
4. 拿到数据后用中文整理输出：实时天气说明天气状况、气温、风向风力、湿度与发布时间；
   预报则按日期列出白天/夜间天气、最高最低气温、风向风力，并给出穿衣、出行或防晒建议。
5. 全程使用中文回答。"""
)
