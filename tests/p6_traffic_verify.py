"""P6 验收：走真实 TrafficSkill 路径，验证火车票与航班查询返回真实数据。"""
import asyncio
import datetime as dt
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_tools.schemas import TrainSearchParms, FlightSearchParms
from skill.traffic_skill import TrafficSkill


def date_after(days: int) -> str:
    return (dt.date.today() + dt.timedelta(days=days)).strftime("%Y-%m-%d")


async def main():
    # 1. 火车票：杭州 → 福州（明天）
    train_params = TrainSearchParms(
        departure_station="杭州", arrival_station="福州", date=date_after(1)
    )
    train_out = await TrafficSkill.search_train(train_params)
    print("=" * 60)
    print(
        f"[火车] {train_out.departure_station} → {train_out.arrival_station} "
        f"{train_out.date} | 命中 {len(train_out.trains)} 班"
    )
    for t in train_out.trains:
        price = " / ".join(t.price_info) or "票价未提供"
        flag = "、".join(t.train_flags)
        print(
            f"  {t.train_no} | {t.departure_time}-{t.arrival_time} | 历时{t.duration} | "
            f"{price} | {'可预定' if t.bookable else '不可预定'} | {flag}"
        )
    print("[建议]", train_out.total_suggest)
    print("=" * 60)

    # 2. 航班：杭州 → 北京（7 天后）
    flight_params = FlightSearchParms(
        departure_city="杭州", arrival_city="北京", date=date_after(7)
    )
    flight_out = await TrafficSkill.search_flight(flight_params)
    print(
        f"[航班] {flight_out.departure_city} → {flight_out.arrival_city} "
        f"{flight_out.date} | 命中 {len(flight_out.flights)} 班"
    )
    for f in flight_out.flights:
        price = f"{f.price:.0f}元" if f.price is not None else "参考价未提供"
        transfer = "直飞" if f.transfer_num == 1 else f"需转机{f.transfer_num}段"
        print(
            f"  {f.flight_no} {f.airline_name} | {f.departure_time}-{f.arrival_time} | "
            f"{f.duration} | {transfer} | 参考价{price}"
        )
    print("[建议]", flight_out.total_suggest)
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())