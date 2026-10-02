from mcp_tools.amap_mcp import RoutePlanMCP, GeomMCP
from mcp_tools.schemas import RoutePlanParms
from mcp_tools.routeSchemas import SimplifyDriveRoute


# 下面这个RouteSkill类提供的方法会给route_agent调用
class RouteSkill:
    def __init__(self):
        self.gen_mcp = GeomMCP()

    @staticmethod
    async def plan_city_route(params: RoutePlanParms) -> SimplifyDriveRoute:
        """根据城市、出行方式、天数、偏好查询路线"""
        return await RoutePlanMCP().execute(params)