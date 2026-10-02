import re
from datetime import date, timedelta
from typing import Dict, List, Optional

from mcp_tools.amap_mcp import WeatherMCP
from mcp_tools.itinerarySchemas import (
    ItineraryDay,
    ItineraryDayCost,
    ItineraryOutput,
    ItineraryParms,
)
from mcp_tools.routeSchemas import RouteDaySegment, RouteSpot
from mcp_tools.schemas import (
    BudgetSearchParms,
    FoodSearchParms,
    HotleSearchParms,
    RoutePlanParms,
    SigleHotelItem,
    SingleFoodItem,
)
from skill.budget_skill import BudgetSkill
from skill.food_skill import FoodSkill
from skill.hotel_skill import HotelSkill
from skill.route_skill import RouteSkill


# 下面这个ItinerarySkill类提供的方法会给itinerary_agent调用
class ItinerarySkill:
    """多日行程编排：把路线分段映射到天，并串联天气/酒店/美食/预算"""

    # 油费估算单价（元/公里），仅作为预算估算口径对外说明
    FUEL_COST_PER_KM = 0.6
    # 每天推荐餐厅数
    TOP_FOODS = 2

    @staticmethod
    async def plan_itinerary(params: ItineraryParms) -> ItineraryOutput:
        """生成 N 天行程：每天含路线分段、景点、天气、住宿、餐饮与费用估算"""
        notes: List[str] = []

        # 1. 路线规划：拿到分段、途经城市、总里程与过路费
        route = await RouteSkill.plan_city_route(
            RoutePlanParms(
                startCity=params.start_city,
                origin_address=params.origin_address,
                endCity=params.end_city,
                dest_address=params.dest_address,
                travel_mode=params.travel_mode,
                travel_days=params.travel_days,
                preference=params.preference,
            )
        )
        if not route.daily_segments:
            raise ValueError("路线规划未返回任何分段，无法编排行程")

        # 2. 把路线分段映射到天（分段少于天数时多出的天为「停留日」）
        day_groups = ItinerarySkill.allocate_days(route.daily_segments, params.travel_days)

        # 3. 逐日组装；天气/酒店/餐饮按城市缓存，避免同城重复请求
        weather_cache: Dict[str, Dict[str, str]] = {}
        hotel_cache: Dict[str, Optional[SigleHotelItem]] = {}
        food_cache: Dict[str, List[SingleFoodItem]] = {}
        day_plans: List[ItineraryDay] = []
        unknown_ticket_days: List[int] = []
        prev_city: Optional[str] = None
        cumulative_km = 0

        for day_num, group in enumerate(day_groups, start=1):
            # 3.1 当日终点城市：按累计里程比例映射到途经城市；停留日沿用前一天
            cumulative_km += sum(seg.distance_km for seg in group)
            if group:
                stay_city = ItinerarySkill.pick_city(
                    route.pass_cities, cumulative_km, route.total_distance_km
                )
                prev_city = stay_city
            else:
                stay_city = prev_city or params.end_city

            distance = sum(seg.distance_km for seg in group)
            drive_hours = round(sum(seg.drive_hours for seg in group), 1)
            road_types = [seg.road_type for seg in group if seg.road_type]
            road_type = road_types[0] if road_types else ""

            # 3.2 沿途景点（按景点名去重），同时汇总门票
            seen_spots: Dict[str, RouteSpot] = {}
            tips: List[str] = []
            for seg in group:
                for spot in seg.scenic_spots:
                    seen_spots.setdefault(spot.spot_name, spot)
                tips.extend(seg.service_info[:2])
                if seg.road_tips:
                    tips.append(seg.road_tips)

            spot_labels: List[str] = []
            ticket_total = 0
            for spot in seen_spots.values():
                price = ItinerarySkill.parse_ticket_price(spot.ticket_price)
                spot_labels.append(
                    f"{spot.spot_name}（门票{spot.ticket_price or '未标明'}，评分{spot.score}）"
                )
                if price is None:
                    unknown_ticket_days.append(day_num)
                else:
                    ticket_total += price

            # 3.3 天气（同城只查一次未来预报）
            if stay_city not in weather_cache:
                weather_cache[stay_city] = await ItinerarySkill.fetch_weather_map(stay_city, notes)
            weather_text = ItinerarySkill.describe_weather(
                weather_cache[stay_city], params.start_date, day_num, stay_city, notes
            )

            # 3.4 住宿与餐饮（同城只查一次）
            if stay_city not in hotel_cache:
                hotel_cache[stay_city] = await ItinerarySkill.fetch_hotel(stay_city, params, notes)
            hotel = hotel_cache[stay_city]

            if stay_city not in food_cache:
                food_cache[stay_city] = await ItinerarySkill.fetch_foods(stay_city, params, notes)
            foods = food_cache[stay_city]

            # 3.5 当日费用：油费按里程估算，过路费按里程占比分摊
            toll_share = 0
            if route.total_distance_km:
                toll_share = round(route.total_toll_fee * distance / route.total_distance_km)
            traffic = round(distance * ItinerarySkill.FUEL_COST_PER_KM) + toll_share

            hotel_price = hotel.price if hotel else None
            priced_foods = [f.price for f in foods if f.price is not None]
            food_price = min(priced_foods) * (params.people or 1) if priced_foods else None
            subtotal = None
            if hotel_price is not None and food_price is not None:
                subtotal = hotel_price + food_price + ticket_total + traffic

            day_plans.append(
                ItineraryDay(
                    day_num=day_num,
                    stay_city=stay_city,
                    route_segments=[seg.section_name for seg in group],
                    distance_km=distance,
                    drive_hours=drive_hours,
                    road_type=road_type,
                    scenic_spots=spot_labels,
                    weather=weather_text,
                    hotel=hotel,
                    foods=foods,
                    cost=ItineraryDayCost(
                        hotel=hotel_price,
                        food=food_price,
                        ticket=ticket_total,
                        traffic=traffic,
                        subtotal=subtotal,
                    ),
                    tips=tips,
                )
            )

        # 4. 汇总预算（复用 BudgetSkill；住宿/餐饮只计入已获取报价的部分）
        fuel_total = round(route.total_distance_km * ItinerarySkill.FUEL_COST_PER_KM)
        traffic_total = fuel_total + route.total_toll_fee
        hotel_total = sum(d.cost.hotel for d in day_plans if d.cost.hotel is not None)
        food_total = sum(d.cost.food for d in day_plans if d.cost.food is not None)
        ticket_all = sum(d.cost.ticket for d in day_plans)

        notes.append(
            f"驾车成本估算口径：油费按 {ItinerarySkill.FUEL_COST_PER_KM} 元/公里 + "
            f"高德预估过路费 {route.total_toll_fee} 元。"
        )
        missing_days = [d.day_num for d in day_plans if d.cost.hotel is None]
        if missing_days:
            notes.append(
                "第 " + "、".join(str(n) for n in missing_days) +
                " 天未获取住宿报价（高德多数酒店不提供挂牌价），住宿费未计入预算，实际花费更高。"
            )
        food_missing_days = [d.day_num for d in day_plans if d.cost.food is None]
        if food_missing_days:
            notes.append(
                "第 " + "、".join(str(n) for n in food_missing_days) +
                " 天未获取餐饮报价，餐饮费按已获取部分估算。"
            )
        if unknown_ticket_days:
            notes.append(
                "第 " + "、".join(str(n) for n in sorted(set(unknown_ticket_days))) +
                " 天有景点门票未标明价格，未计入门票费。"
            )

        budget = await BudgetSkill.calculate_budget(
            BudgetSearchParms(
                traffic_cost=traffic_total,
                hotel_cost=hotel_total or None,
                food_cost=food_total or None,
                tick_cost=ticket_all,
                people=params.people or 1,
                travel_days=params.travel_days,
            )
        )

        return ItineraryOutput(
            origin=route.origin,
            destination=route.destination,
            travel_days=params.travel_days,
            travel_mode=params.travel_mode or "驾车",
            people=params.people or 1,
            total_distance_km=route.total_distance_km,
            total_drive_hours=route.total_drive_hours,
            total_toll_fee=route.total_toll_fee,
            route_strategy=route.route_strategy,
            days=day_plans,
            budget=budget,
            global_tips=route.global_tips,
            notes=notes,
        )

    # ====================== 内部工具 ======================
    @staticmethod
    def allocate_days(
        segments: List[RouteDaySegment], travel_days: int
    ) -> List[List[RouteDaySegment]]:
        """把路线分段映射到天，返回按天分组的列表（空分组表示当日停留不移动）

        - 段数少于天数：每段先分 1 天，剩余天数按驾驶时长从长到短依次插为「停留日」
        - 段数多于天数：按顺序均匀合并，保证天数连续
        """
        if not segments:
            return []
        count = len(segments)
        if travel_days <= 0:
            return [[seg] for seg in segments]
        if travel_days < count:
            groups: List[List[RouteDaySegment]] = [[] for _ in range(travel_days)]
            for index, seg in enumerate(segments):
                groups[index * travel_days // count].append(seg)
            return groups

        # 每段先占 1 天，再把剩余天数按驾驶时长排序依次追加为停留日
        order = sorted(range(count), key=lambda i: segments[i].drive_hours, reverse=True)
        rest_after = [0] * count
        for extra in range(travel_days - count):
            rest_after[order[extra % count]] += 1

        groups = []
        for index, seg in enumerate(segments):
            groups.append([seg])
            groups.extend([] for _ in range(rest_after[index]))
        return groups

    @staticmethod
    def pick_city(pass_cities: List[str], cumulative_km: int, total_km: int) -> str:
        """按累计里程占全程的比例，把当天终点映射到途经城市列表中的城市

        路线分段的 section_name 用的是路口/枢纽名（如「南外环路」「东坑互通」），
        直接截取会得到「南外环路」这种非城市名，导致天气/酒店/美食查询落到错误城市，
        因此改用 pass_cities（有序途经城市）按里程比例插值。
        """
        if not pass_cities:
            return ""
        if total_km <= 0:
            return pass_cities[-1]
        ratio = min(max(cumulative_km / total_km, 0.0), 1.0)
        return pass_cities[round(ratio * (len(pass_cities) - 1))]

    @staticmethod
    def parse_ticket_price(text: str) -> Optional[int]:
        """解析门票价格字符串：「免费」→0，「60元」→60，无法解析→None（不编造）"""
        if not text:
            return None
        if "免费" in text:
            return 0
        numbers = re.findall(r"\d+", text)
        return int(numbers[0]) if numbers else None

    @staticmethod
    async def fetch_weather_map(city: str, notes: List[str]) -> Dict[str, str]:
        """取该城市未来预报，返回 日期 → 天气描述 映射（查不到时记入 notes）"""
        try:
            resp = await WeatherMCP().execute(city, "", "all")
        except Exception as exc:
            notes.append(f"{city}：天气查询失败（{exc}），当天天气未获取。")
            return {}
        result: Dict[str, str] = {}
        if resp.forecasts:
            for cast in resp.forecasts[0].casts:
                result[cast.date] = (
                    f"{cast.dayweather}转{cast.nightweather}，{cast.daytemp}~{cast.nighttemp}℃"
                )
        return result

    @staticmethod
    def describe_weather(
        weather_map: Dict[str, str],
        start_date: Optional[str],
        day_num: int,
        city: str,
        notes: List[str],
    ) -> Optional[str]:
        """按出发日期匹配当天预报；超出预报范围时用最后一天做趋势参考并如实说明"""
        if not weather_map:
            return None
        if start_date:
            try:
                target = (date.fromisoformat(start_date) + timedelta(days=day_num - 1)).isoformat()
            except ValueError:
                target = None
            if target and target in weather_map:
                return f"{target} {weather_map[target]}"
            if target:
                notes.append(f"{city} 第 {day_num} 天（{target}）超出 4 天预报范围，天气仅供参考。")
        dates = sorted(weather_map)
        picked = dates[day_num - 1] if day_num <= len(dates) else dates[-1]
        return f"{picked}（趋势参考）{weather_map[picked]}"

    @staticmethod
    async def fetch_hotel(
        city: str, params: ItineraryParms, notes: List[str]
    ) -> Optional[SigleHotelItem]:
        """取该城市一家推荐住宿：优先有报价且最便宜的，便于预算估算"""
        try:
            out = await HotelSkill.search_hotel(
                HotleSearchParms(city=city, price_max=params.hotel_price_max)
            )
        except Exception as exc:
            notes.append(f"{city}：酒店查询失败（{exc}），当天住宿未获取。")
            return None
        if not out.recommend_hotels:
            notes.append(f"{city}：未查到酒店。")
            return None
        priced = [h for h in out.recommend_hotels if h.price is not None]
        return min(priced, key=lambda h: h.price) if priced else out.recommend_hotels[0]

    @staticmethod
    async def fetch_foods(
        city: str, params: ItineraryParms, notes: List[str]
    ) -> List[SingleFoodItem]:
        """取该城市餐饮推荐（默认前 2 家）"""
        try:
            out = await FoodSkill.search_food(
                FoodSearchParms(city=city, cuisine=params.food_cuisine)
            )
        except Exception as exc:
            notes.append(f"{city}：美食查询失败（{exc}），当天餐饮未获取。")
            return []
        return out.recommend_foods[: ItinerarySkill.TOP_FOODS]