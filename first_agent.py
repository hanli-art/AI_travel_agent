# AgentFirst.py
import os
import asyncio
import requests
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from openai import AsyncOpenAI
from agents import Agent, OpenAIChatCompletionsModel, Runner, function_tool
from monitor_hook import MonitorHooks
# 在 load_dotenv() 之前或之后都可以
os.environ["OPENAI_AGENTS_DISABLE_TRACING"] = "true"
# 加载环境变量
load_dotenv()
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
DASHSCOPE_BASE_URL = os.getenv("DASHSCOPE_BASE_URL")
MODEL_NAME = os.getenv("MODEL_NAME")
AMAP_KEY = os.getenv("AMAP_KEY")

# 1. 定义天气数据结构 (Pydantic模型)
class Weather(BaseModel):
    city: str = Field(description="城市名称")
    weather_info: str = Field(description="天气情况的描述")
    temperature: str = Field(description="温度")

# 2. 设计查询天气的工具函数
@function_tool
def SearchWeather(city: str, address: str = "") -> Weather:
    """
    通过城市名称和详细地址查询高德天气信息。
    Args:
        city: 城市名称，比如：北京、上海
        address: 详细地址（可选），比如：北京市朝阳区阜通东大街6号
    Returns:
        Weather: 包含城市、天气情况、温度的对象
    """
    # 第一步：地理编码，获取 adcode（区域编码）
    # 提示：高德天气API其实可以直接传城市名，但为了巩固你的逻辑，保留你截图中的地理编码步骤
    geo_url = "https://restapi.amap.com/v3/geocode/geo"
    
    # ⚠️ 注意这里修正了你的参数传反问题
    geo_params = {
        "key": AMAP_KEY,
        "city": city,     # 修正：city 是城市名
        "address": address, # 修正：address 是详细地址
        "output": "json"
    }
    
    geo_res = requests.get(geo_url, params=geo_params, timeout=5).json()
    
    if geo_res.get("status") != "1" or not geo_res.get("geocodes"):
        raise ValueError(f"获取城市地理位置编码失败: {geo_res.get('info', '未知错误')}")
        
    adcode = geo_res["geocodes"][0]["adcode"]  # 获取到城市编码

    # 第二步：调用高德天气 API 获取实时天气
    weather_url = "https://restapi.amap.com/v3/weather/weatherInfo"
    weather_params = {
        "key": AMAP_KEY,
        "city": adcode,       # 用刚才拿到的 adcode 查询更精准
        "extensions": "base", # base 代表实况天气
        "output": "json"
    }
    
    weather_res = requests.get(weather_url, params=weather_params, timeout=5).json()
    
    if weather_res.get("status") != "1" or not weather_res.get("lives"):
        raise ValueError(f"获取天气信息失败: {weather_res.get('info', '未知错误')}")
        
    # 提取天气数据
    live = weather_res["lives"][0]
    return Weather(
        city=live["city"],
        weather_info=live["weather"],
        temperature=live["temperature"] # 返回的可能是字符串，如 "24"
    )

# 3. 创建智能体并绑定工具
client = AsyncOpenAI(api_key=DASHSCOPE_API_KEY, base_url=DASHSCOPE_BASE_URL)
main_agent = Agent(
    name='main_agent',
    model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=client),
    tools=[SearchWeather] # 👈 必须在这里把工具注册给智能体，大模型才知道有这个能力
)

# 4. 执行对话测试
async def LLM_Chat():
    print("第一轮对话：上海今天天气怎么样？")
    result = await Runner.run(main_agent, "上海今天天气怎么样？")
    print(result.final_output)
    
    print("-" * 30)
    print("第二轮对话：帮我查一下北京市朝阳区阜通东大街6号的天气")
    result = await Runner.run(main_agent, "帮我查一下北京市朝阳区阜通东大街6号的天气")
    print(result.final_output)

if __name__ == "__main__":
    asyncio.run(LLM_Chat())