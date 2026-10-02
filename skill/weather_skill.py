from mcp_tools.amap_mcp import WeatherMCP
from mcp_tools.schemas import AmapWeatherResponse


# 下面这个WeatherSkill类提供的方法会给weather_agent调用
class WeatherSkill:
    @staticmethod
    async def query_weather(
        city: str, address: str = "", extensions: str = "base"
    ) -> AmapWeatherResponse:
        """查询城市实时天气（base）或未来预报（all）"""
        return await WeatherMCP().execute(city, address, extensions)
