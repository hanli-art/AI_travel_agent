"""
聚合数据交通 MCP：火车票站到站时刻/票价查询 + 航班时刻/参考票价查询

接口依据聚合数据官方文档：
- 火车订票查询（ID:817）：https://apis.juhe.cn/fapigw/train/query
- 航班订票查询（ID:818）：https://apis.juhe.cn/flight/query
"""
import datetime as dt
from typing import Any, Dict, List, Optional

import requests

from config import JUHE_TRAIN_KEY, JUHE_FLIGHT_KEY
from mcp_tools.base_mcp import BaseMCP
from mcp_tools.schemas import (
    TrainSearchParms,
    SingleTrainItem,
    TrainSearchOutput,
    FlightSearchParms,
    SingleFlightItem,
    FlightSearchOutput,
)

TRAIN_URL = "https://apis.juhe.cn/fapigw/train/query"
FLIGHT_URL = "https://apis.juhe.cn/flight/query"

# 火车票接口仅允许查询未来 15 天内的日期（官方硬性约束）
TRAIN_DATE_LIMIT_DAYS = 15

# 常见城市 → IATA 城市三字码（航班接口只认三字码，用城市名会报参数错误）
CITY_IATA = {
    "北京": "BJS", "上海": "SHA", "广州": "CAN", "深圳": "SZX",
    "杭州": "HGH", "南京": "NKG", "成都": "CTU", "重庆": "CKG",
    "西安": "SIA", "武汉": "WUH", "长沙": "CSX", "厦门": "XMN",
    "福州": "FOC", "昆明": "KMG", "贵阳": "KWE", "南宁": "NNG",
    "郑州": "CGO", "青岛": "TAO", "大连": "DLC", "沈阳": "SHE",
    "哈尔滨": "HRB", "天津": "TSN", "济南": "TNA", "三亚": "SYX",
    "海口": "HAK", "丽江": "LJG", "大理": "DLU", "乌鲁木齐": "URC",
    "兰州": "LHW", "银川": "INC", "呼和浩特": "HET", "太原": "TYN",
    "南昌": "KHN", "合肥": "HFE", "宁波": "NGB", "温州": "WNZ",
    "无锡": "WUX", "桂林": "KWL", "拉萨": "LXA",
}


class TrainMCP(BaseMCP):
    """火车票查询：站到站时刻表 + 各席别票价"""
    name: str = "train_mcp"
    description: str = "输入出发站+到达站+日期，返回火车班次时刻与票价"
    # 最多返回班次数，避免班次过多撑爆上下文
    MAX_TRAINS = 8

    @staticmethod
    def _check_date(date: str) -> str:
        """校验日期格式并限制在未来 15 天内（接口硬性约束）"""
        try:
            target = dt.datetime.strptime(str(date).strip(), "%Y-%m-%d").date()
        except ValueError:
            raise ValueError(f"日期格式应为 YYYY-MM-DD，收到：{date}")
        delta = (target - dt.date.today()).days
        if delta < 0:
            raise ValueError("火车票只能查询今天或未来的日期")
        if delta > TRAIN_DATE_LIMIT_DAYS:
            raise ValueError(f"火车票只能查询未来 {TRAIN_DATE_LIMIT_DAYS} 天内的日期")
        return target.strftime("%Y-%m-%d")

    @staticmethod
    def _format_prices(prices: Any) -> List[str]:
        """把票价数组格式化为可读字符串

        官方文档只说明 prices 为「票价信息」数组，未公开子字段名，
        故对常见键名做兼容取值，取不到时原样透传，避免编造席别与价格。
        """
        result: List[str] = []
        if not isinstance(prices, list):
            return result
        seat_keys = ("seat_name", "seat", "seat_type", "name", "type")
        price_keys = ("price", "cost", "amount", "ticket_price")
        for item in prices:
            if isinstance(item, dict):
                seat = next((item[k] for k in seat_keys if item.get(k)), "")
                price = next(
                    (item[k] for k in price_keys if item.get(k) is not None), ""
                )
                if seat and price != "":
                    result.append(f"{seat} ¥{price}")
                elif seat:
                    result.append(str(seat))
                elif item:
                    result.append(" ".join(f"{k}={v}" for k, v in item.items()))
            elif item:
                result.append(str(item))
        return result

    @staticmethod
    def _build_suggest(params: TrainSearchParms, trains: List[SingleTrainItem]) -> str:
        """生成购票总体建议（无结果时如实说明，不编造班次）"""
        if not trains:
            return (
                f"未查询到 {params.departure_station} → {params.arrival_station} "
                f"在 {params.date} 的班次，可尝试把站点写得更具体（如「杭州东」）"
                f"或调整日期后重试。"
            )
        priced = [t for t in trains if t.price_info]
        parts = [f"共返回 {len(trains)} 个班次，其中 {len(priced)} 个提供票价。"]
        flags = sorted({f for t in trains for f in t.train_flags})
        if flags:
            parts.append(f"列车标签：{'、'.join(flags)}。")
        parts.append("火车票建议尽早购买，热门车次容易售罄，以 12306 实际售票为准。")
        return "".join(parts)

    async def execute(self, params: TrainSearchParms) -> TrainSearchOutput:
        if not JUHE_TRAIN_KEY:
            raise ValueError(
                "未配置 JUHE_TRAIN_KEY，请在 .env 中填写火车订票查询接口的 appkey"
            )
        date = self._check_date(params.date)
        # search_type=1 表示按站点名称查询
        req_params: Dict[str, Any] = {
            "key": JUHE_TRAIN_KEY,
            "search_type": 1,
            "departure_station": params.departure_station,
            "arrival_station": params.arrival_station,
            "date": date,
            # 2=返回全部班次，避免只看可预定导致结果为空
            "enable_booking": 2,
        }
        if params.train_filter:
            req_params["filter"] = params.train_filter
        if params.departure_time_range:
            req_params["departure_time_range"] = params.departure_time_range

        res = requests.get(TRAIN_URL, params=req_params).json()
        if res.get("error_code") != 0:
            raise ValueError(f"聚合数据火车票接口返回错误：{res.get('reason', res)}")

        trains: List[SingleTrainItem] = []
        for raw in (res.get("result") or [])[: self.MAX_TRAINS]:
            trains.append(
                SingleTrainItem(
                    train_no=raw.get("train_no", ""),
                    departure_station=raw.get("departure_station", ""),
                    arrival_station=raw.get("arrival_station", ""),
                    departure_time=raw.get("departure_time", ""),
                    arrival_time=raw.get("arrival_time", ""),
                    duration=raw.get("duration", ""),
                    price_info=self._format_prices(raw.get("prices")),
                    train_flags=[f for f in (raw.get("train_flags") or []) if f],
                    bookable=str(raw.get("enable_booking", "")).upper() == "Y",
                )
            )
        return TrainSearchOutput(
            departure_station=params.departure_station,
            arrival_station=params.arrival_station,
            date=date,
            trains=trains,
            total_suggest=self._build_suggest(params, trains),
        )


class FlightMCP(BaseMCP):
    """航班查询：两城之间的航班时刻与参考票价"""
    name: str = "flight_mcp"
    description: str = "输入出发城市+到达城市+日期，返回航班时刻与参考票价"
    # 最多返回航班数
    MAX_FLIGHTS = 8

    @staticmethod
    def resolve_iata(city: str) -> str:
        """城市名 → IATA 三字码；已是三字码则原样返回"""
        text = str(city or "").strip()
        if len(text) == 3 and text.isalpha():
            return text.upper()
        code = CITY_IATA.get(text)
        if not code:
            raise ValueError(
                f"暂不支持的城市「{text}」，请改用 IATA 三字码（如杭州 HGH、北京 BJS）"
            )
        return code

    @staticmethod
    def _build_suggest(params: FlightSearchParms, flights: List[SingleFlightItem]) -> str:
        """生成航班出行建议（无结果时如实说明）"""
        if not flights:
            return (
                f"未查询到 {params.departure_city} → {params.arrival_city} "
                f"在 {params.date} 的航班，可尝试调整日期或允许中转后重试。"
            )
        direct = [f for f in flights if f.transfer_num == 1]
        parts = [f"共返回 {len(flights)} 个航班，其中直飞 {len(direct)} 个。"]
        priced = [f.price for f in flights if f.price is not None]
        if priced:
            parts.append(
                f"参考票价 {min(priced):.0f}-{max(priced):.0f} 元，实际以出票价格为准。"
            )
        else:
            parts.append("接口未提供参考票价，请以实际出票价格为准。")
        parts.append("建议提前关注航班动态，预留值机与安检时间。")
        return "".join(parts)

    async def execute(self, params: FlightSearchParms) -> FlightSearchOutput:
        if not JUHE_FLIGHT_KEY:
            raise ValueError(
                "未配置 JUHE_FLIGHT_KEY，请在 .env 中填写航班订票查询接口的 appkey"
            )
        req_params: Dict[str, Any] = {
            "key": JUHE_FLIGHT_KEY,
            "departure": self.resolve_iata(params.departure_city),
            "arrival": self.resolve_iata(params.arrival_city),
            "departureDate": params.date,
            # 0=任意航段，1=仅直飞
            "maxSegments": 1 if params.direct_only else 0,
        }
        res = requests.get(FLIGHT_URL, params=req_params).json()
        if res.get("error_code") != 0:
            raise ValueError(f"聚合数据航班接口返回错误：{res.get('reason', res)}")

        raw_list = (res.get("result") or {}).get("flightInfo") or []
        flights: List[SingleFlightItem] = []
        for raw in raw_list[: self.MAX_FLIGHTS]:
            price = raw.get("ticketPrice")
            flights.append(
                SingleFlightItem(
                    airline_name=raw.get("airlineName") or raw.get("airline", ""),
                    flight_no=raw.get("flightNo", ""),
                    departure_airport=raw.get("departureName") or raw.get("departure", ""),
                    arrival_airport=raw.get("arrivalName") or raw.get("arrival", ""),
                    departure_time=raw.get("departureTime", ""),
                    arrival_time=raw.get("arrivalTime", ""),
                    duration=raw.get("duration", ""),
                    transfer_num=int(raw.get("transferNum") or 1),
                    price=float(price) if price not in (None, "") else None,
                )
            )
        # 按出发时间排序，方便用户比较
        flights.sort(key=lambda f: f.departure_time)
        return FlightSearchOutput(
            departure_city=params.departure_city,
            arrival_city=params.arrival_city,
            date=params.date,
            flights=flights,
            total_suggest=self._build_suggest(params, flights),
        )