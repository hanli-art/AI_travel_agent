import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()
AMAP_KEY = os.getenv("AMAP_KEY")

# 高德 API 基础请求函数
def _request_amap_api(url: str, params: dict) -> dict:
    """通用的高德API请求方法，包含异常处理和超时控制"""
    if not AMAP_KEY:
        return {"status": "0", "info": "AMAP_KEY 未配置，请检查 .env 文件"}
        
    params["key"] = AMAP_KEY
    params["output"] = "json"
    
    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()  # 如果状态码不是200，抛出异常
        return response.json()
    except requests.exceptions.Timeout:
        return {"status": "0", "info": "请求高德API超时"}
    except requests.exceptions.RequestException as e:
        return {"status": "0", "info": f"请求高德API失败: {str(e)}"}

# ==================== 1. 地理编码与天气 ====================

def get_geocode(city: str, address: str = "") -> dict:
    """将地址转换为经纬度或获取城市的 adcode"""
    url = "https://restapi.amap.com/v3/geocode/geo"
    params = {"city": city, "address": address}
    return _request_amap_api(url, params)

def get_weather(city: str) -> str:
    """查询城市实时天气，返回格式化 JSON 字符串供大模型阅读"""
    # 先获取 adcode
    geo_data = get_geocode(city)
    if geo_data.get("status") != "1" or not geo_data.get("geocodes"):
        return json.dumps({"error": f"找不到城市 {city} 的地理编码"}, ensure_ascii=False)
    
    adcode = geo_data["geocodes"][0]["adcode"]
    
    url = "https://restapi.amap.com/v3/weather/weatherInfo"
    params = {"city": adcode, "extensions": "base"}
    data = _request_amap_api(url, params)
    
    if data.get("status") == "1" and data.get("lives"):
        # 按照你之前的逻辑，提取关键信息，让大模型理解更轻松
        live = data["lives"][0]
        weather_info = {
            "省份": live.get("province"),
            "城市": live.get("city"),
            "天气": live.get("weather"),
            "温度": live.get("temperature"),
            "风向": live.get("winddirection"),
            "风力": live.get("windpower"),
            "湿度": live.get("humidity"),
            "更新时间": live.get("reporttime")
        }
        return json.dumps(weather_info, ensure_ascii=False, indent=2)
    else:
        return json.dumps({"error": f"获取天气失败: {data.get('info')}"}, ensure_ascii=False)

# ==================== 2. POI 搜索（酒店/景点/餐饮） ====================

def search_poi(keywords: str, city: str, types: str = "") -> str:
    """
    搜索景点、酒店、餐饮等地点。
    types 可选参数（高德分类代码）：如 100000（景点），100100（住宿），050000（餐饮）
    """
    url = "https://restapi.amap.com/v3/place/text"
    params = {
        "keywords": keywords,
        "city": city,
        "citylimit": "true", # 仅返回指定城市数据
        "offset": 5,         # 返回前5条结果
        "page": 1
    }
    if types:
        params["types"] = types
        
    data = _request_amap_api(url, params)
    
    if data.get("status") == "1" and data.get("pois"):
        results = []
        for poi in data["pois"]:
            results.append({
                "名称": poi.get("name"),
                "地址": poi.get("address"),
                "经纬度": poi.get("location"),
                "类型": poi.get("type"),
                "评分": poi.get("biz_ext", {}).get("rating", "暂无评分"),
                "门票价格": poi.get("biz_ext", {}).get("cost", "暂无")
            })
        return json.dumps(results, ensure_ascii=False, indent=2)
    else:
        return json.dumps({"error": f"未找到相关POI: {data.get('info')}"}, ensure_ascii=False)

# ==================== 3. 路径规划（自驾/步行） ====================

def get_driving_route(origin: str, destination: str) -> str:
    """
    自驾路线规划。
    origin/destination 格式为："经度,纬度"（例如："116.481028,39.989643"）
    如果只有城市名，请先调用 get_geocode 获取经纬度。
    """
    url = "https://restapi.amap.com/v3/direction/driving"
    params = {
        "origin": origin,
        "destination": destination,
        "extensions": "all", # 返回详细信息，如服务区、路况等
        "strategy": 10       # 综合策略（可调节）
    }
    data = _request_amap_api(url, params)
    
    if data.get("status") == "1" and data.get("route"):
        route = data["route"]
        summary = {
            "起点": origin,
            "终点": destination,
            "总距离_km": route.get("paths")[0].get("distance"),
            "预计耗时_分钟": route.get("paths")[0].get("duration"),
            "过路费_元": route.get("paths")[0].get("tolls"),
            "分段导航": []
        }
        # 提取前几个关键步骤，防止Token过大
        steps = route.get("paths")[0].get("steps", [])[:5]
        for step in steps:
            summary["分段导航"].append({
                "指示": step.get("instruction"),
                "道路": step.get("road"),
                "距离_米": step.get("distance"),
                "耗时_秒": step.get("duration")
            })
        return json.dumps(summary, ensure_ascii=False, indent=2)
    else:
        return json.dumps({"error": f"路线规划失败: {data.get('info')}"}, ensure_ascii=False)

# ==================== 4. 测试代码（单独运行时测试） ====================
if __name__ == "__main__":
    print("测试天气查询：")
    print(get_weather("福州"))
    
    print("\n测试POI搜索（福州景点）：")
    print(search_poi("三坊七巷", "福州", types="100000"))
    
    print("\n测试自驾路线规划（北京到天津）：")
    # 实际调用前需要先获取经纬度，这里写死测试
    print(get_driving_route("116.481028,39.989643", "117.200983,39.084158"))