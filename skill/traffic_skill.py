from mcp_tools.juhe_mcp import TrainMCP, FlightMCP
from mcp_tools.schemas import (
    TrainSearchParms,
    TrainSearchOutput,
    FlightSearchParms,
    FlightSearchOutput,
)


# 下面这个TrafficSkill类提供的方法会给traffic_agent调用
class TrafficSkill:
    @staticmethod
    async def search_train(params: TrainSearchParms) -> TrainSearchOutput:
        """按出发站+到达站+日期查询火车班次与票价"""
        return await TrainMCP().execute(params)

    @staticmethod
    async def search_flight(params: FlightSearchParms) -> FlightSearchOutput:
        """按出发城市+到达城市+日期查询航班时刻与参考票价"""
        return await FlightMCP().execute(params)