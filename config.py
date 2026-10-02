import os
from dotenv import load_dotenv
from openai import AsyncOpenAI
from agents import OpenAIChatCompletionsModel

load_dotenv()
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
DASHSCOPE_BASE_URL = os.getenv("DASHSCOPE_BASE_URL")
MODEL_NAME = os.getenv("MODEL_NAME")
AMAP_KEY = os.getenv("AMAP_KEY")
# 聚合数据按接口分配 appkey：火车与航班各一个，未单独配置时回退到通用 JUHE_KEY
JUHE_KEY = os.getenv("JUHE_KEY")
JUHE_TRAIN_KEY = os.getenv("JUHE_TRAIN_KEY") or JUHE_KEY
JUHE_FLIGHT_KEY = os.getenv("JUHE_FLIGHT_KEY") or JUHE_KEY

# 初始化底层客户端和模型实例，供所有 Agent 共享
client = AsyncOpenAI(api_key=DASHSCOPE_API_KEY, base_url=DASHSCOPE_BASE_URL)
model = OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=client)