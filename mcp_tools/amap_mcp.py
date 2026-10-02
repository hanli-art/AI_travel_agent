"""
高德地图 MCP ，所有天气查询，路线规划、酒店查询、地理编码、实时天气、景点查询
"""
import json
import os
import math
import requests
from typing import Dict, Any, List, Optional
from config import AMAP_KEY
from dotenv import load_dotenv
from mcp_tools.base_mcp import BaseMCP
from mcp_tools.schemas import (
    LiveWeather,
    HotleSearchParms, 
    SigleHotelItem, 
    RoutePlanParms,
    AmapWeatherResponse,
    HotelSearchOutput
)
from mcp_tools.routeSchemas import RouteSpot, SimplifyDriveRoute,RouteDaySegment, SpotPhoto
# 风景名胜大类编码
SCENIC_TYPE = "060000"

class GeomMCP(BaseMCP):
    """地理编码：获取经纬度"""
    name: str = "geo_mcp"
    description: str = "输入城市+地址，返回经纬度"
        
    async def execute(self, city: str, address: str = ""):
        url = "https://restapi.amap.com/v3/geocode/geo"
        req_params = {
            "key": AMAP_KEY,
            "city": city,
            "address": address,
            "output": "json",
        }
        res = requests.get(url, params=req_params).json()
        if res.get("status") == "1":
            return res["geocodes"][0]["location"]
        else:
            raise ValueError(f"高德地理编码返回错误：{res.get('info', res)}")


class WeatherMCP(BaseMCP):
    """实时天气：获取城市实时天气"""
    name: str = "weather_mcp"
    description: str = "输入城市，返回实时天气"

    async def execute(self, city:str,address:str)->AmapWeatherResponse:
        location =await GeomMCP().execute(city,address)
        
        url="https://restapi.amap.com/v3/weather/now"
        params={
            "key":AMAP_KEY,
            "city":location,
            "output":"json"
        }
        res=requests.get(url,params=params).json()
        if res.get("status")=="1":
            return AmapWeatherResponse.model_validate(res["now"])
        else:
            raise ValueError(f"高德地图返回错误：{res['info']}")

        
class RoutePlanMCP(BaseMCP):
    """路线规划：根据城市、出行方式、天数、偏好查询路线"""
    name: str = "route_plan_mcp"
    description: str = "输入城市+出行方式+天数+偏好，返回路线规划"
    # 需要直接删除的冗余字段（匹配需求：坐标串、编码、埋点、polyline等）
    DEL_FIELDS = {
        "polyline", "citycode", "adcode", "tollId", "linkId", "routeId",
        "tmcs", "taxi_cost", "districts", "orientation", "action", "assistant_action"
    }

    @staticmethod
    def clean_poi_to_spot(poi_raw:dict,max_img=3)->Optional[RouteSpot]:
        """
        将高德原始POI数据清洗为轻量化RouteSpot模型
        限制图片数量，拆分tag为简介数组
        """
        name=poi_raw.get("name", "")
        if not name:
            return None
        #拆分标签做为简短介绍
        tag_raw=poi_raw.get("tag", "")
        if isinstance(tag_raw, list):
            tag_list=[t.strip() for t in tag_raw if t.strip()]
        elif isinstance(tag_raw, str) and tag_raw.strip():
            tag_list=[t.strip() for t in tag_raw.split(",") if t.strip()]
        else:
            tag_list=[]
        #景点类
        type_full=poi_raw.get("type", "")
        #基础业务信息
        biz_ext=poi_raw.get("biz_ext", {})
        score=float(biz_ext.get("rating",0.0)) if biz_ext.get("rating") else 0.0
        ticket=biz_ext.get("const","未知")
        open_time=biz_ext.get("open_time","全体开放")

        #清洗图片，最多保留max_img张图片
        photo_list=[]
        raw_photos=poi_raw.get("photos",[])
        for p in raw_photos[:max_img]:
            p_url = p.get("url")
            p_title = p.get("title")
            photo=SpotPhoto(
                photo_url=(p_url if isinstance(p_url, str) else ""),
                photo_description=(p_title if isinstance(p_title, str) else "景点实拍")
            )
            photo_list.append(photo)

        spot =RouteSpot(
            spot_name=name,
            spot_type=type_full,
            short_intro_tags=tag_list,
            score=score,
            ticket_price=ticket,
            open_hour=open_time,
            spot_images=photo_list
        )
        return spot

    @staticmethod
    def search_amap_scenic(city:str,keyword:str="",limit:int=5)->str:
        """
        高德POI关键词搜索景区，返回轻量化景点JSON数组
        Args:
            city: 城市名称，如大理、南昌、福州
            keyword: 可选景点关键词，为空则只搜风景名胜大类
            limit: 返回景点数量上限
    Returns:
        压缩JSON字符串，元素为RouteSpot轻量化景点数据
        """
        url="https://restapi.amap.com/v3/place/text"
        params={
            "key":AMAP_KEY,
            "city":city,
            "types":SCENIC_TYPE,
            "extensions":"all",
            "output":"json",

        }
        if keyword:
            params["keywords"]=keyword
        try:    
            res=requests.get(url,params=params).json()
            if res.get("status")!="1":
                print(res.get("info",res))
                return res.get("info",res)
            #拆分标签作为简短介绍
            pois = res.get("pois", [])[:limit]
            spot_result=[]
            for p in pois:
                spot=RoutePlanMCP.clean_poi_to_spot(p)
                if spot:
                    spot_result.append(spot.model_dump())

            return json.dumps(spot_result,separators=(",",":"))
        except Exception as e:
            print(f"高德地图Poi景点检索异常：{str(e)}")
            err={"error":f"高德地图返回错误：{str(e)}"}
            return json.dumps(err,separators=(",",":"))
    




    @staticmethod
    def meter_to_km(meter: int) -> int:
        """米转公里，四舍五入"""
        return math.ceil(meter / 1000) if meter % 1000 != 0 else meter // 1000
    @staticmethod
    def second_to_hour(second: int) -> float:
        """秒转小时，保留1位小数"""
        return round(second / 3600, 1)

    

# ====================== 高德原始JSON清洗核心工具函数 ======================
    @staticmethod
    def get_road_type_from_road_name(road_name: str) -> str:
        """根据道路名称判断道路类型"""
        if "高速" in road_name:
            return "高速"
        elif "国道" in road_name:
            return "国道"
        elif "山" in road_name or "盘山" in road_name:
            return "山路"
        else:
            return "城区道路"          
    @staticmethod
    def extract_pass_cities(route_cities: List[Dict[str, Any]]) -> List[str]:
        """提取途经城市名称，过滤citycode/adcode编码"""
        city_names = []
        for city_item in route_cities:
            city_name = city_item.get("name")
            if city_name and city_name not in city_names:
                city_names.append(city_name)
        return city_names


    @staticmethod
    def aggregate_steps(steps: List[Dict[str, Any]], city: str = None) -> List[RouteDaySegment]:
        """
        核心路段聚合逻辑：合并连续同类型道路
        输入：原始高德step小段列表, city为目的地城市用于搜索沿线景点
        输出：聚合后的大分段RouteDaySegment数组（含景点信息）
        """
        if not steps:
            return []

        agg_segments = []
        # 初始化第一段
        current_road_name = steps[0].get("road", "")
        current_road_type = RoutePlanMCP.get_road_type_from_road_name(current_road_name)
        start_point = current_road_name
        total_meter = int(steps[0].get("distance", 0) or 0)
        total_second = int(steps[0].get("duration", 0) or 0)
        toll_count = 1 if int(steps[0].get("tolls", 0) or 0) > 0 else 0
        tunnel_count = 0
        road_tip_list = []

        for step in steps[1:]:
            road_name = step.get("road", "")
            road_type = RoutePlanMCP.get_road_type_from_road_name(road_name)

            # 同类型道路，合并
            if road_type == current_road_type:
                total_meter += int(step.get("distance", 0) or 0)
                total_second += int(step.get("duration", 0) or 0)
                toll_count += 1 if int(step.get("tolls", 0) or 0) > 0 else 0
                # 路况提示收集
                if step.get("instruction"):
                    if any(keyword in step["instruction"] for keyword in ["弯道", "长下坡", "隧道"]):
                        road_tip_list.append(step["instruction"])
            # 不同类型道路，保存上一段，开启新分段
            else:
                # 生成配套设施描述
                service_info = []
                if toll_count > 0:
                    service_info.append(f"收费站{toll_count}个")
                if tunnel_count > 0:
                    service_info.append(f"隧道{tunnel_count}处")
                # 路况提示合并
                road_tip = "，".join(list(set(road_tip_list))) if road_tip_list else "路况平稳，正常驾驶"
                # 区间名称
                section_name = f"{start_point} → {current_road_name}"
                seg = RouteDaySegment(
                    section_name=section_name,
                    distance_km=RoutePlanMCP.meter_to_km(total_meter),
                    drive_hours=RoutePlanMCP.second_to_hour(total_second),
                    road_type=current_road_type,
                    service_info=service_info,
                    scenic_spots=[],
                    road_tips=road_tip
                )
                agg_segments.append(seg)
                # 重置当前分段
                current_road_type = road_type
                start_point = current_road_name
                current_road_name = road_name
                total_meter = int(step.get("distance", 0) or 0)
                total_second = int(step.get("duration", 0) or 0)
                toll_count = 1 if int(step.get("tolls", 0) or 0) > 0 else 0
                road_tip_list = []

        # 循环结束，处理最后一段
        service_info = []
        if toll_count > 0:
            service_info.append(f"收费站{toll_count}个")
        road_tip = "，".join(list(set(road_tip_list))) if road_tip_list else "路况平稳，正常驾驶"
        last_section = RouteDaySegment(
            section_name=f"{start_point} → {current_road_name}",
            distance_km=RoutePlanMCP.meter_to_km(total_meter),
            drive_hours=RoutePlanMCP.second_to_hour(total_second),
            road_type=current_road_type,
            service_info=service_info,
            scenic_spots=[],
            road_tips=road_tip
        )
        agg_segments.append(last_section)

        # ===== 聚合完成后，补充景点信息 =====
        if city and agg_segments:
            spot_json = RoutePlanMCP.search_amap_scenic(city)
            try:
                spot_dicts = json.loads(spot_json)
                if isinstance(spot_dicts, list):
                    # 筛除非景点数据（如错误信息）
                    valid_spots = [s for s in spot_dicts if isinstance(s, dict) and "spot_name" in s]
                    if valid_spots:
                        # 只分配到非高速路段
                        stoppable = [s for s in agg_segments if s.road_type != "高速"] or agg_segments
                        for i, s in enumerate(valid_spots):
                            stoppable[i % len(stoppable)].scenic_spots.append(RouteSpot(**s))
            except Exception as e:
                # 景点检索失败不应中断路线规划，仅记录日志
                print(f"高德地图Poi景点检索异常：{str(e)}")
        
        return agg_segments

    @staticmethod
    def generate_global_tips(path_data: Dict[str, Any]) -> List[str]:
        """生成全局出行提示：限行、高速、山路通用提醒"""
        tips = []
        # 限行判断：restriction=1代表有无法规避限行
        if path_data.get("restriction", 0) == 1:
            tips.append("本路线包含限行路段，出行前确认外地车辆限行规则")
        # 高速提示
        has_highway = any("高速" in step.get("road", "") for step in path_data.get("steps", []))
        if has_highway:
            tips.append("高速路段多隧道，进出隧道注意切换车灯，保持安全车距")
        # 山路提示
        has_mountain = any("山" in step.get("road", "") for step in path_data.get("steps", []))
        if has_mountain:
            tips.append("山区弯道路段较多，雨天路面易打滑，尽量避免夜间行驶")
        return tips    

    @staticmethod
    def clean_amap_raw_data(raw_resp:Dict[str,Any], dest_city:str="")->SimplifyDriveRoute:
        """
        入口主函数：原始高德API响应 → 清洗聚合 → SimplifyDriveRoute模型
        :param raw_resp: 高德驾车规划完整返回json字典
        :param dest_city: 目的地城市，用于搜索沿线景点
        :return: SimplifyDriveRoute 实例（可直接model_dump_json发给LLM）
        """
        # 1. 基础状态校验
        if raw_resp.get("status") != "1":
            raise ValueError(f"高德接口请求失败，错误信息：{raw_resp.get('info')}")
        route_root = raw_resp.get("route", {})
        if not route_root:
            raise ValueError("未获取到驾车路线数据")
        path_list = route_root.get("paths", [])
        if not path_list:
            raise ValueError("无驾车方案paths数据")
        path_data = path_list[0]

        # 2. 提取顶层基础数值
        total_meter = int(path_data.get("distance", 0) or 0)
        total_second = int(path_data.get("duration", 0) or 0)
        total_toll = int(path_data.get("tolls", 0) or 0)
        strategy = path_data.get("strategy", "未知路线策略")
        origin_coord = route_root.get("origin", "")
        dest_coord = route_root.get("destination", "")
        # 模拟起点终点名称（实际业务替换为逆地理编码地址）
        origin_name = f"起点坐标{origin_coord}"
        dest_name = f"终点坐标{dest_coord}"

        # 3. 途经城市提取
        raw_cities = path_data.get("cities", [])
        pass_cities = RoutePlanMCP.extract_pass_cities(raw_cities)

        # 使用目的地城市搜索景点，若未传入则取途经城市最后一个
        scenic_city = dest_city or (pass_cities[-1] if pass_cities else "")

        # 4. 路段聚合（传入城市以搜索沿线景点）
        raw_steps = path_data.get("steps", [])
        daily_segments = RoutePlanMCP.aggregate_steps(raw_steps, city=scenic_city)
        print(daily_segments)
        # 5. 判断是否存在山路
        has_mountain_road = any(seg.road_type == "山路" for seg in daily_segments)
        print("vvvvvvvvvvvvvvvvvvvvvvvvvvv")
        # 6. 全局出行提示
        global_tips = RoutePlanMCP.generate_global_tips(path_data)

        # 7. 组装输出模型
        clean_model = SimplifyDriveRoute(
            origin=origin_name,
            destination=dest_name,
            pass_cities=pass_cities,
            total_distance_km=RoutePlanMCP.meter_to_km(total_meter),
            total_drive_hours=RoutePlanMCP.second_to_hour(total_second),
            total_toll_fee=total_toll,
            route_strategy=strategy,
            has_mountain_road=has_mountain_road,
            daily_segments=daily_segments,
            global_tips=global_tips
        )
        return clean_model


    async def execute(self, params: RoutePlanParms) -> SimplifyDriveRoute:
        city = params.endCity
        travel_mode = params.travel_mode
        total_days = params.travel_days
        preference = params.preference
        geo = GeomMCP()
        origin = await geo.execute(params.startCity, params.origin_address or "")
        dest = await geo.execute(params.endCity, params.dest_address or "")
        url = "https://restapi.amap.com/v3/direction/driving"
        req_params = {
            "key": AMAP_KEY,
            "origin": origin,
            "destination": dest,
            "strategy": preference or "0",
            "output": "json",
        }
        res = requests.get(url, params=req_params).json()

        cleaned_res = RoutePlanMCP.clean_amap_raw_data(res, dest_city=params.endCity)
        #print(cleaned_res)      
        return cleaned_res
        
    # 新增：获取原始JSON数据（不做Pydantic校验）

class HotelSearchMCP(BaseMCP):
    """酒店查询：根据城市、价格范围、入住人群类型、入住天数查询酒店"""
    name: str = "hotel_m_mcp"
    description: str = "输入城市+价格范围+入住人群类型+入住天数，返回酒店列表"

    async def execute(self, params:HotleSearchParms)->HotelSearchOutput:
        city=params.city
        price_min=params.price_min
        price_max=params.price_max
        crowd=params.crowd
        stay_days=params.stay_days
        address=params.address
    # 2. 调用高德地理编码获取酒店位置
        url="https://restapi.amap.com/v3/place/around"
        params={
            "key":AMAP_KEY,
            "city":city,
            "price_min":price_min,
            "price_max":price_max,
            "crowd":crowd,
            "stay_days":stay_days,
            "address":address,
            "output":"json"
        }
        res=requests.get(url,params=params).json()
        location=res["geocode"][0]["location"]
        #3根据位置周搜索酒店列表
        search_url = "https://restapi.amap.com/v3/place/around"
        search_params={
            "key":AMAP_KEY,
            "city":city,
            "price_min":price_min,
            "price_max":price_max,
            "crowd":crowd,
            "stay_days":stay_days,
            "location":location,
            "radius":3000,
            "output":"json"
        }
        search_res=requests.get(search_url,params=search_params).json()
        # 4. 原始API数据映射为结构化输出Schema
        hotel_list=[]
        for poi in search_res.get("pois",[])[:5]:
            hotel_item =SigleHotelItem(
                hotel_name=poi.get("name","未知酒店"),
                address=poi.get("address",""),
                avg_price=(price_min+price_max)//2 ,
                crowd=crowd
            )
            hotel_list.append(hotel_item)
        output=HotelSearchOutput(
            recommend_hotels=hotel_list,
            city=city,
            total_suggest=stay_days*price_max
        )
        return output



        
       

        