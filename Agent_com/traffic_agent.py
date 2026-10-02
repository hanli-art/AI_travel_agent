from agents import Agent
from config import model

traffic_agent = Agent(
    name='traffic_agent',
    model=model,
    instructions="""你是机票/火车票购买与交通出行专家。
要求：
1. 根据用户提供的出发地、目的地和日期，提供合理的交通方式建议（飞机/高铁）。
2. 提醒用户提前购票，并给出大致票价预估（或根据工具查询）。
3. 结合高德地图数据，给出从车站/机场到目的地的接驳建议。
4. 中文输出，条理清晰。""",
    # tools=[search_train_flight] # 👈 后续把相关交通搜索工具加上
)