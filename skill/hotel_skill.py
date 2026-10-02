from mcp_tools.amap_mcp import HotelSearchMCP
from mcp_tools.schemas import HotleSearchParms, HotelSearchOutput


# 下面这个HotelSkill类提供的方法会给hotel_agent调用
class HotelSkill:
    @staticmethod
    async def search_hotel(params: HotleSearchParms) -> HotelSearchOutput:
        """按城市+地址查询周边真实酒店，返回名称/地址/价格/评分"""
        return await HotelSearchMCP().execute(params)