from mcp_tools.amap_mcp import FoodSearchMCP
from mcp_tools.schemas import FoodSearchParms, FoodSearchOutput


# 下面这个FoodSkill类提供的方法会给food_agent调用
class FoodSkill:
    @staticmethod
    async def search_food(params: FoodSearchParms) -> FoodSearchOutput:
        """按城市+菜系+人均预算查询真实餐厅，返回名称/人均/菜系/评分/地址"""
        return await FoodSearchMCP().execute(params)