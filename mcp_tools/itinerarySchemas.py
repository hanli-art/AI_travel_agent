from pydantic import BaseModel, Field
from typing import List, Optional

from mcp_tools.schemas import (
    BudgetSearchOutput,
    SigleHotelItem,
    SingleFoodItem,
)


# ====================== 多日行程编排（P9） ======================
class ItineraryParms(BaseModel):
    """多日行程编排入参"""
    start_city: str = Field(description="出发城市,如：福州")
    end_city: str = Field(description="目的地城市,如：杭州")
    travel_days: int = Field(description="行程天数,如：6（6天5夜传 6）")
    travel_mode: Optional[str] = Field(default="驾车", description="出行方式,如：驾车/火车/飞机")
    origin_address: Optional[str] = Field(default=None, description="出发地址,可选")
    dest_address: Optional[str] = Field(default=None, description="目的地地址,可选")
    people: Optional[int] = Field(default=1, description="出行人数,默认1人")
    start_date: Optional[str] = Field(default=None, description="出发日期 YYYY-MM-DD,可选,用于匹配天气预报")
    preference: Optional[str] = Field(default=None, description="路线偏好,如：高速优先")
    food_cuisine: Optional[str] = Field(default=None, description="沿途餐饮偏好菜系,可选")
    hotel_price_max: Optional[int] = Field(default=None, description="酒店每晚预算上限,单位：元,可选")


class ItineraryDayCost(BaseModel):
    """单日费用估算（各项均来自真实查询数据，无报价时为 None）"""
    hotel: Optional[int] = Field(default=None, description="当晚住宿参考价,单位：元")
    food: Optional[int] = Field(default=None, description="当日餐饮参考价,单位：元（人均×人数）")
    ticket: int = Field(default=0, description="当日景点门票合计,单位：元（免费为 0）")
    traffic: int = Field(default=0, description="当日驾车成本估算,单位：元（油费+过路费分摊）")
    subtotal: Optional[int] = Field(default=None, description="当日小计,单位：元（住宿或餐饮缺报价时为 None）")


class ItineraryDay(BaseModel):
    """逐日行程"""
    day_num: int = Field(description="第几天")
    stay_city: str = Field(description="当日到达/住宿城市")
    route_segments: List[str] = Field(default_factory=list, description="当日路线分段（区间名）")
    distance_km: int = Field(default=0, description="当日里程,单位：km")
    drive_hours: float = Field(default=0.0, description="当日纯驾驶时长,单位：小时")
    road_type: str = Field(default="", description="道路类型：高速/国道/城区道路/山路")
    scenic_spots: List[str] = Field(default_factory=list, description="当日沿途景点（名称+门票+评分）")
    weather: Optional[str] = Field(default=None, description="当日天气（预报或趋势参考）")
    hotel: Optional[SigleHotelItem] = Field(default=None, description="当日推荐住宿")
    foods: List[SingleFoodItem] = Field(default_factory=list, description="当日餐饮推荐")
    cost: ItineraryDayCost = Field(default_factory=ItineraryDayCost, description="当日费用估算")
    tips: List[str] = Field(default_factory=list, description="当日路况与出行提示")


class ItineraryOutput(BaseModel):
    """多日行程编排结果"""
    origin: str = Field(description="出发地名称+地址")
    destination: str = Field(description="目的地名称+地址")
    travel_days: int = Field(description="行程天数")
    travel_mode: str = Field(description="出行方式")
    people: int = Field(description="出行人数")
    total_distance_km: int = Field(description="全程总里程,单位：km")
    total_drive_hours: float = Field(description="全程纯驾驶总时长,单位：小时")
    total_toll_fee: int = Field(description="全程预估过路费,单位：元")
    route_strategy: str = Field(default="", description="路线策略")
    days: List[ItineraryDay] = Field(default_factory=list, description="逐日行程")
    budget: Optional[BudgetSearchOutput] = Field(default=None, description="全程预算汇总")
    global_tips: List[str] = Field(default_factory=list, description="全局出行提示")
    notes: List[str] = Field(default_factory=list, description="数据缺失与估算口径说明")