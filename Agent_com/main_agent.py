from agents import Agent, handoff
from config import model
from Agent_com.route_agent import route_agent
from Agent_com.hotel_agent import hotel_agent
from Agent_com.traffic_agent import traffic_agent
from Agent_com.weather_agent import weather_agent
from Agent_com.food_agent import food_agent

main_agent = Agent(
    name="agent_manager",
    model=model,
    handoffs=[
        handoff(route_agent),
        handoff(hotel_agent),
        handoff(traffic_agent),
        handoff(weather_agent),
        handoff(food_agent),
    ],
    instructions="""你是旅游智能体总指挥，负责协调其它智能体处理任务：
- 路线规划：调用 route_agent
- 酒店住宿：调用 hotel_agent
- 机票/火车票购买：调用 traffic_agent
- 天气查询：调用 weather_agent
- 美食推荐：调用 food_agent
特别注意整个大模型思考过程输出要显示中文。
收到用户请求后，请仔细分析意图，调用对应的子智能体来完成任务。"""
)