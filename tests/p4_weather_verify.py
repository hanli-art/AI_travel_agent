"""P4 验收：走真实 WeatherSkill 路径，验证实时天气与未来预报。"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from skill.weather_skill import WeatherSkill


async def main():
    live = await WeatherSkill.query_weather("杭州", "雷峰塔", "base")
    print("=" * 50)
    print("[实时天气] status:", live.status, "| info:", live.info)
    for w in live.lives or []:
        print(
            f"  {w.province}{w.city}({w.adcode}) {w.weather} {w.temperature}℃ "
            f"{w.winddirection}风{w.windpower}级 湿度{w.humidity}% @ {w.reporttime}"
        )

    fc = await WeatherSkill.query_weather("大理", "", "all")
    print("-" * 50)
    print("[未来预报] status:", fc.status, "| info:", fc.info)
    for city in fc.forecasts or []:
        print(f"  {city.province}{city.city}({city.adcode}) @ {city.reporttime}")
        for c in city.casts:
            print(
                f"    {c.date}(周{c.week}) 白天{c.dayweather}{c.daytemp}℃ "
                f"夜间{c.nightweather}{c.nighttemp}℃ {c.daywind}风{c.daypower}级"
            )
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
