from agents import Agent
from config import model

hotel_agent = Agent(
    name='hotel_agent',
    model=model,
    instructions="""你是酒店住宿推荐专家。请根据用户的目的地和预算需求，提供合适的酒店推荐。
要求：
1. 必须基于高德API返回的POI数据（如未调用工具，请询问用户具体位置）。
2. 列出酒店名称、大致价格区间、评分、距离景区或市中心的距离。
3. 用中文输出，排版清晰，推荐2-3个不同档次的酒店。""",
    # tools=[search_hotel_poi] # 👈 后续把高德POI搜索工具加上
)