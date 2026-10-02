"""P9 验收：路线分段映射到天 + 串联多子 Agent 输出逐日行程。

用法：python tests/p9_itinerary_verify.py [--full]
不带 --full 只验证天数映射逻辑（不调用接口）；带 --full 跑真实「福州→杭州 6天5夜」。
"""
import asyncio
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_tools.itinerarySchemas import ItineraryParms
from mcp_tools.routeSchemas import RouteDaySegment
from skill.itinerary_skill import ItinerarySkill


def fake_segment(name: str, km: int, hours: float, spot: str = "") -> RouteDaySegment:
    """构造测试用分段"""
    return RouteDaySegment(
        section_name=name,
        distance_km=km,
        drive_hours=hours,
        road_type="高速",
        service_info=[f"{name}服务区"],
        scenic_spots=[],
        road_tips=f"{name}注意限速",
    )


def check_mapping():
    """验证天数映射：段数少于/等于/多于天数三种情况"""
    segments = [
        fake_segment("福州鼓楼区 -> 南平延平区", 180, 2.4),
        fake_segment("南平延平区 -> 上饶信州区", 200, 2.6),
        fake_segment("上饶信州区 -> 衢州柯城区", 130, 1.8),
        fake_segment("衢州柯城区 -> 杭州西湖区", 240, 3.0),
        fake_segment("杭州西湖区 -> 杭州临安区", 60, 1.0),
    ]
    print("=" * 68)
    print("[天数映射] 共 5 个路线分段")
    for days in (2, 5, 6, 8):
        groups = ItinerarySkill.allocate_days(segments, days)
        total_seg = sum(len(g) for g in groups)
        assert len(groups) == days, f"天数 {days} 应为 {days} 组，实际 {len(groups)}"
        assert total_seg == len(segments), f"天数 {days} 分段数丢失：{total_seg}"
        desc = " | ".join(
            f"D{i + 1}:" + ("停留" if not g else "+".join(s.section_name for s in g))
            for i, g in enumerate(groups)
        )
        print(f"  {days} 天 → {desc}")
    print("[结果] 天数、分段数均守恒，映射逻辑通过")
    print("=" * 68)


async def check_full():
    """真实编排：福州 → 杭州 6 天 5 夜"""
    start = (date.today() + timedelta(days=1)).isoformat()
    params = ItineraryParms(
        start_city="福州",
        end_city="杭州",
        travel_days=6,
        people=2,
        travel_mode="驾车",
        start_date=start,
    )
    out = await ItinerarySkill.plan_itinerary(params)
    print("=" * 68)
    print(f"[行程] {out.origin} -> {out.destination}")
    print(
        f"[总览] {out.travel_days}天 | {out.travel_mode} | {out.people}人 | "
        f"总里程 {out.total_distance_km}km | 总驾驶 {out.total_drive_hours}h | "
        f"过路费 {out.total_toll_fee}元 | 策略 {out.route_strategy}"
    )
    for d in out.days:
        print("-" * 68)
        print(
            f"第{d.day_num}天 | 到达 {d.stay_city} | {d.distance_km}km / "
            f"{d.drive_hours}h | {d.road_type}"
        )
        print(f"  路线分段: {'、'.join(d.route_segments) or '当日停留，不移动'}")
        print(f"  沿途景点: {'、'.join(d.scenic_spots) or '无'}")
        print(f"  天气: {d.weather or '未获取'}")
        if d.hotel:
            price = f"{d.hotel.price}元" if d.hotel.price is not None else "价格需预订时确认"
            print(f"  住宿: {d.hotel.hotel_name} | {price} | 评分{d.hotel.score} | {d.hotel.address}")
        else:
            print("  住宿: 未获取")
        if d.foods:
            for f in d.foods:
                price = f"{f.price}元" if f.price is not None else "价格以实际消费为准"
                print(f"  餐饮: {f.food_name} | {price} | 评分{f.score}")
        else:
            print("  餐饮: 未获取")
        print(
            f"  费用: 住宿{d.cost.hotel} 餐饮{d.cost.food} 门票{d.cost.ticket} "
            f"交通{d.cost.traffic} 小计{d.cost.subtotal}"
        )
        if d.tips:
            print(f"  提示: {'；'.join(d.tips)}")
    print("-" * 68)
    if out.budget:
        b = out.budget
        print(
            f"[预算] 总计 {b.total_cost}元 | 人均 {b.per_person_cost}元 | "
            f"日均 {b.daily_average}元"
        )
        for item in b.breakdown:
            print(f"  {item.item_name}: {item.cost}元 ({item.ratio * 100:.1f}%)")
    print("[全局提示]")
    for tip in out.global_tips:
        print(f"  - {tip}")
    print("[说明]")
    for note in out.notes:
        print(f"  - {note}")
    print("=" * 68)


if __name__ == "__main__":
    check_mapping()
    if "--full" in sys.argv:
        asyncio.run(check_full())
    else:
        print("（加 --full 参数跑真实编排，会调用高德接口）")