"""
高德地图 MCP ，所有天气查询，路线规划、酒店查询、地理编码、实时天气、景点查询
"""
import json
import os
import re
import time
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
# 高德 POI 大类编码：110000=风景名胜（060000 实为购物服务，会导致景点全是商场）
SCENIC_TYPE = "110000"

class GeomMCP(BaseMCP):
    """地理编码：获取经纬度 / adcode"""
    name: str = "geo_mcp"
    description: str = "输入城市+地址，返回经纬度"

    async def execute(self, city: str, address: str = ""):
        """返回经纬度（location）

        高德地理编码要求 address 非空，否则返回 INVALID_PARAMS；
        路线规划常只给城市名，故 address 为空时回退用城市名当地址。
        """
        url = "https://restapi.amap.com/v3/geocode/geo"
        req_params = {
            "key": AMAP_KEY,
            "city": city,
            "address": address or city,
            "output": "json",
        }
        res = requests.get(url, params=req_params).json()
        if res.get("status") == "1":
            return res["geocodes"][0]["location"]
        else:
            raise ValueError(f"高德地理编码返回错误：{res.get('info', res)}")

    @staticmethod
    async def get_adcode(city: str, address: str = "") -> str:
        """返回城市 adcode

        天气接口的 city 参数只认 adcode，传经纬度会报错，故单独提供。
        高德地理编码要求 address 非空，只给城市名时会报 INVALID_PARAMS，故回退用城市名当地址。
        """
        url = "https://restapi.amap.com/v3/geocode/geo"
        req_params = {
            "key": AMAP_KEY,
            "city": city,
            "address": address or city,
            "output": "json",
        }
        res = requests.get(url, params=req_params).json()
        if res.get("status") == "1" and res.get("geocodes"):
            return res["geocodes"][0]["adcode"]
        raise ValueError(f"高德地理编码返回错误：{res.get('info', res)}")


class WeatherMCP(BaseMCP):
    """天气查询：实时天气（base）+ 未来预报（all）"""
    name: str = "weather_mcp"
    description: str = "输入城市+地址+查询类型，返回实时天气或未来预报"

    async def execute(
        self, city: str, address: str = "", extensions: str = "base"
    ) -> AmapWeatherResponse:
        """extensions: base=实时天气(lives)，all=未来预报(forecasts)"""
        adcode = await GeomMCP.get_adcode(city, address)
        url = "https://restapi.amap.com/v3/weather/weatherInfo"
        params = {
            "key": AMAP_KEY,
            "city": adcode,
            "extensions": extensions,
            "output": "json",
        }
        res = requests.get(url, params=params).json()
        if res.get("status") == "1":
            return AmapWeatherResponse.model_validate(res)
        raise ValueError(f"高德天气接口返回错误：{res.get('info', res)}")

        
class RoutePlanMCP(BaseMCP):
    """路线规划：根据城市、出行方式、天数、偏好查询路线"""
    name: str = "route_plan_mcp"
    description: str = "输入城市+出行方式+天数+偏好，返回路线规划"
    # 需要直接删除的冗余字段（匹配需求：坐标串、编码、埋点、polyline等）
    DEL_FIELDS = {
        "polyline", "citycode", "adcode", "tollId", "linkId", "routeId",
        "tmcs", "taxi_cost", "districts", "orientation", "action", "assistant_action"
    }
    # 中文路线偏好 → 高德 strategy 编码
    STRATEGY_MAP = {
        "速度优先": "0", "时间优先": "0", "高速优先": "0", "综合": "0",
        "费用优先": "1", "最少收费": "1", "经济": "1",
        "距离优先": "2", "最短距离": "2",
        "不走高速": "3", "避免高速": "3",
        "避免拥堵": "4",
    }
    DEFAULT_STRATEGY = "0"
    # 高德 strategy 编码 → 中文描述
    STRATEGY_LABEL = {
        "0": "速度优先", "1": "费用优先", "2": "距离优先", "3": "不走高速",
        "4": "避免拥堵", "5": "多策略", "6": "避免拥堵且不走高速",
        "7": "避免拥堵且费用优先", "8": "避免拥堵且距离优先",
        "9": "不走高速且避免拥堵", "10": "不走高速且避免收费",
    }
    # 里程短于该值的异类路段并入相邻段，避免分段过碎
    SHORT_SEGMENT_METER = 10000
    # 高德 v3 驾车接口的 tolls 字段恒为 0（实测），改由 toll_distance 估算过路费
    TOLL_RATE_PER_KM = 0.45

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
        ticket=biz_ext.get("cost") or "未知"
        open_time=biz_ext.get("open_time") or "全天开放"

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
            # 默认搜「风景区」，否则只按大类取会返回村口小广场这类低知名度 POI
            "keywords":keyword or "风景区",
            "extensions":"all",
            "output":"json",
        }
        try:
            # 高德个人 Key 有并发/QPS 限制，触发 CUQPS 时限流重试
            res={}
            for attempt in range(3):
                res=requests.get(url,params=params).json()
                if res.get("status")=="1":
                    break
                if "CUQPS" in str(res.get("info","")):
                    time.sleep(0.5*(attempt+1))
                    continue
                break
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

    @staticmethod
    def resolve_strategy(preference: str) -> str:
        """把中文路线偏好转换为高德 strategy 编码

        此前直接把「风景优先」这类中文传给高德，属于非法取值，策略未生效。
        已是数字编码的原样返回。
        """
        if not preference:
            return RoutePlanMCP.DEFAULT_STRATEGY
        text = str(preference).strip()
        if text.isdigit():
            return text
        for keyword, code in RoutePlanMCP.STRATEGY_MAP.items():
            if keyword in text:
                return code
        return RoutePlanMCP.DEFAULT_STRATEGY

    

# ====================== 高德原始JSON清洗核心工具函数 ======================
    @staticmethod
    def infer_road_type(road_name: str, instruction: str = "", fallback: str = "城区道路") -> str:
        """结合道路名与导航指令判断道路类型

        高德 step 的 road 常是隧道/枢纽名（如「竹海隧道」「洋门枢纽」），
        真正在跑的高速/国道只写在 instruction 里（如「途径G25长深高速」）。
        只看 road 会把长距离高速误标为城区道路，因此必须两者结合。
        road 为空代表匝道/路口，沿用上一段类型，避免连续高速被切碎。
        """
        text = f"{road_name or ''} {instruction or ''}"
        if "高速" in text or re.search(r"[GS]\d{1,4}", text):
            return "高速"
        if "国道" in text or re.search(r"\d{3}国道", text):
            return "国道"
        if "山路" in text or "盘山" in text:
            return "山路"
        if not road_name:
            return fallback
        return "城区道路"

    @staticmethod
    def extract_pass_cities(steps: List[Dict[str, Any]]) -> List[str]:
        """提取途经城市名称

        高德 v3 驾车接口的途经城市挂在每个 step 的 cities 字段上，
        route.cities 恒为空，因此必须遍历 steps 收集（需 extensions=all）。
        """
        city_names = []
        for step in steps:
            for city_item in step.get("cities") or []:
                city_name = city_item.get("name") if isinstance(city_item, dict) else None
                if city_name and city_name not in city_names:
                    city_names.append(city_name)
        return city_names


    @staticmethod
    def aggregate_steps(
        steps: List[Dict[str, Any]],
        origin_label: str = "起点",
        dest_label: str = "终点",
    ) -> List[RouteDaySegment]:
        """
        核心路段聚合逻辑：按道路类型切段并合并，避免分段过碎
        1. 逐步推断道路类型（匝道/路口沿用上一段类型）
        2. 合并连续同类型 step
        3. 里程短于 SHORT_SEGMENT_METER 的 run 并入相邻段
        输入：原始高德step小段列表
        输出：聚合后的RouteDaySegment数组
        """
        if not steps:
            return []

        # 1. 逐步推断道路类型
        typed_steps: List[Any] = []
        prev_type = "城区道路"
        for step in steps:
            road_type = RoutePlanMCP.infer_road_type(
                step.get("road", ""), step.get("instruction", ""), fallback=prev_type
            )
            prev_type = road_type
            typed_steps.append((step, road_type))

        # 2. 合并连续同类型 step → run
        runs: List[Dict[str, Any]] = []
        for step, road_type in typed_steps:
            if runs and runs[-1]["type"] == road_type:
                runs[-1]["steps"].append(step)
            else:
                runs.append({"type": road_type, "steps": [step]})

        def run_meter(run: Dict[str, Any]) -> int:
            return sum(int(s.get("distance") or 0) for s in run["steps"])

        # 3. 短 run 并入前一段
        merged: List[Dict[str, Any]] = []
        for run in runs:
            if merged and run_meter(run) < RoutePlanMCP.SHORT_SEGMENT_METER:
                merged[-1]["steps"].extend(run["steps"])
            else:
                merged.append({"type": run["type"], "steps": list(run["steps"])})

        # 首段过短则并入下一段（无前段可并）
        if len(merged) > 1 and run_meter(merged[0]) < RoutePlanMCP.SHORT_SEGMENT_METER:
            merged[1]["steps"] = merged[0]["steps"] + merged[1]["steps"]
            merged.pop(0)

        # 4. 二次合并：吸收短段后可能出现相邻同类型
        final_runs: List[Dict[str, Any]] = []
        for run in merged:
            if final_runs and final_runs[-1]["type"] == run["type"]:
                final_runs[-1]["steps"].extend(run["steps"])
            else:
                final_runs.append(run)

        # 5. 生成分段，段名取「上段末道路 → 下段首道路」
        type_tips = {
            "高速": "高速为主，隧道较多，进出隧道注意车灯并保持车距",
            "国道": "国道路段，注意对向来车与沿途路口",
            "山路": "山区弯道较多，雨天路面易打滑，尽量避免夜间行驶",
            "城区道路": "途经城区道路，注意红绿灯、限速与行人",
        }
        segments: List[RouteDaySegment] = []
        prev_end = origin_label
        for idx, run in enumerate(final_runs):
            run_steps = run["steps"]
            start_name = (run_steps[0].get("road") or "").strip() or prev_end
            if idx + 1 < len(final_runs):
                next_road = (final_runs[idx + 1]["steps"][0].get("road") or "").strip()
                end_name = next_road or (run_steps[-1].get("road") or "").strip() or dest_label
            else:
                end_name = dest_label

            tunnel_count = sum(1 for s in run_steps if "隧道" in (s.get("instruction") or ""))
            service_count = sum(
                1 for s in run_steps
                if any(k in (s.get("instruction") or "") for k in ("服务区", "收费站"))
            )
            service_info = []
            if tunnel_count:
                service_info.append(f"隧道{tunnel_count}处")
            if service_count:
                service_info.append(f"服务区/收费站{service_count}处")

            road_tips = type_tips.get(run["type"], "路况平稳，正常驾驶")
            if any("长下坡" in (s.get("instruction") or "") for s in run_steps):
                road_tips += "；含长下坡路段，注意控制车速"

            segments.append(
                RouteDaySegment(
                    section_name=f"{start_name} → {end_name}",
                    distance_km=RoutePlanMCP.meter_to_km(run_meter(run)),
                    drive_hours=RoutePlanMCP.second_to_hour(
                        sum(int(s.get("duration") or 0) for s in run_steps)
                    ),
                    road_type=run["type"],
                    service_info=service_info,
                    scenic_spots=[],
                    road_tips=road_tips,
                )
            )
            prev_end = end_name

        return segments

    @staticmethod
    def attach_scenic_spots(
        segments: List[RouteDaySegment], cities: List[str], per_city: int = 3
    ) -> None:
        """按途经城市顺序搜索景点，就近分配到对应分段

        此前只用终点城市搜景点、再轮流塞给所有分段，会把杭州的商场分到福州出发段。
        这里按城市先后把分段切成对应区间，第 k 个城市的景点只落在第 k 个区间。
        """
        if not segments or not cities:
            return

        seg_count = len(segments)
        city_count = len(cities)
        for idx, city in enumerate(cities):
            if not city:
                continue
            if idx > 0:
                # 逐城检索，间隔请求规避高德 QPS 限制
                time.sleep(0.35)
            try:
                spot_json = RoutePlanMCP.search_amap_scenic(city, limit=per_city)
                spots = json.loads(spot_json)
            except Exception as e:
                print(f"景点检索失败 city={city}: {str(e)}")
                continue
            if not isinstance(spots, list):
                continue

            valid_spots = [
                s for s in spots if isinstance(s, dict) and s.get("spot_name")
            ]
            if not valid_spots:
                continue

            start = idx * seg_count // city_count
            end = max(start + 1, (idx + 1) * seg_count // city_count)
            bucket = segments[start:end]
            if not bucket:
                continue
            for i, spot in enumerate(valid_spots):
                bucket[i % len(bucket)].scenic_spots.append(RouteSpot(**spot))

    @staticmethod
    def generate_global_tips(
        path_data: Dict[str, Any], segments: Optional[List[RouteDaySegment]] = None
    ) -> List[str]:
        """生成全局出行提示：限行、高速、山路通用提醒

        高速/山路判断以聚合后的分段类型为准，避免用 road 字段误判
        （road 常是含「山」的隧道名，会把纯高速路线判成山路）。
        """
        tips = []
        # 限行判断：restriction=1代表有无法规避限行（接口返回字符串）
        if str(path_data.get("restriction", 0)) == "1":
            tips.append("本路线包含限行路段，出行前确认外地车辆限行规则")
        road_types = {seg.road_type for seg in segments} if segments else set()
        if "高速" in road_types:
            tips.append("高速路段多隧道，进出隧道注意切换车灯，保持安全车距")
        if "山路" in road_types:
            tips.append("山区弯道路段较多，雨天路面易打滑，尽量避免夜间行驶")
        return tips

    @staticmethod
    def clean_amap_raw_data(
        raw_resp: Dict[str, Any],
        dest_city: str = "",
        origin_label: str = "起点",
        dest_label: str = "终点",
    ) -> SimplifyDriveRoute:
        """
        入口主函数：原始高德API响应 → 清洗聚合 → SimplifyDriveRoute模型
        :param raw_resp: 高德驾车规划完整返回json字典
        :param dest_city: 目的地城市（无途经城市时兜底搜景点）
        :param origin_label: 起点展示名
        :param dest_label: 终点展示名
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
        # 高德 v3 的 tolls 恒为 0，用收费里程估算过路费
        reported_toll = int(path_data.get("tolls", 0) or 0)
        toll_meter = int(path_data.get("toll_distance", 0) or 0)
        total_toll = (
            reported_toll
            if reported_toll > 0
            else round(toll_meter / 1000 * RoutePlanMCP.TOLL_RATE_PER_KM)
        )
        # strategy 字段高德已直接返回中文（如「速度最快」），仅数字编码才查表
        strategy_raw = str(path_data.get("strategy", "") or "")
        if strategy_raw.isdigit():
            strategy_label = RoutePlanMCP.STRATEGY_LABEL.get(strategy_raw, "综合策略")
        else:
            strategy_label = strategy_raw or "综合策略"

        # 3. 途经城市提取（需请求时带 extensions=all，城市挂在 step.cities）
        pass_cities = RoutePlanMCP.extract_pass_cities(path_data.get("steps", []))

        # 4. 路段聚合
        daily_segments = RoutePlanMCP.aggregate_steps(
            path_data.get("steps", []),
            origin_label=origin_label,
            dest_label=dest_label,
        )

        # 5. 景点按途经城市就近分配；无途经城市时退化为终点城市
        scenic_cities = pass_cities or ([dest_city] if dest_city else [])
        RoutePlanMCP.attach_scenic_spots(daily_segments, scenic_cities)

        # 6. 判断是否存在山路
        has_mountain_road = any(seg.road_type == "山路" for seg in daily_segments)

        # 7. 全局出行提示（以聚合分段类型为准）
        global_tips = RoutePlanMCP.generate_global_tips(path_data, daily_segments)

        # 8. 组装输出模型
        return SimplifyDriveRoute(
            origin=origin_label,
            destination=dest_label,
            pass_cities=pass_cities,
            total_distance_km=RoutePlanMCP.meter_to_km(total_meter),
            total_drive_hours=RoutePlanMCP.second_to_hour(total_second),
            total_toll_fee=total_toll,
            route_strategy=strategy_label,
            has_mountain_road=has_mountain_road,
            daily_segments=daily_segments,
            global_tips=global_tips,
        )


    async def execute(self, params: RoutePlanParms) -> SimplifyDriveRoute:
        geo = GeomMCP()
        origin = await geo.execute(params.startCity, params.origin_address or "")
        dest = await geo.execute(params.endCity, params.dest_address or "")
        url = "https://restapi.amap.com/v3/direction/driving"
        req_params = {
            "key": AMAP_KEY,
            "origin": origin,
            "destination": dest,
            # 中文偏好（如「高速优先」）需转成高德策略编码，否则策略不生效
            "strategy": RoutePlanMCP.resolve_strategy(params.preference),
            # 途经城市、收费里程等字段仅在 extensions=all 时返回
            "extensions": "all",
            "output": "json",
        }
        res = requests.get(url, params=req_params).json()

        origin_label = params.origin_address or params.startCity
        dest_label = params.dest_address or params.endCity
        cleaned_res = RoutePlanMCP.clean_amap_raw_data(
            res,
            dest_city=params.endCity,
            origin_label=origin_label,
            dest_label=dest_label,
        )
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



        
       

        