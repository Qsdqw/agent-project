import os
import hashlib
import random
import requests
from datetime import datetime

from langchain_core.tools import tool
from utils.config_loader import agent_conf
from utils.path_tool import get_abs_path
from utils.logger import logger
from rag.rag_service import RagSummarizeService
from storage.redis_client import get_redis
from tenacity import retry, stop_after_attempt, wait_fixed

_rag = None
external_data = {}


def _get_rag() -> RagSummarizeService:
    global _rag
    if _rag is None:
        _rag = RagSummarizeService()
    return _rag

RAG_CACHE_TTL = 86400  # 24 小时


@tool(description="从向量存储中检索参考资料")
def rag_summarize(query: str) -> str:
    r = get_redis()
    cache_key = f"rag:cache:{hashlib.sha256(query.encode()).hexdigest()}"
    cached = r.get(cache_key)
    if cached is not None:
        return cached

    result = _get_rag().rag_summarize(query)
    r.set(cache_key, result, ex=RAG_CACHE_TTL)
    return result


@retry(stop=stop_after_attempt(2), wait=wait_fixed(2), reraise=True)
def _fetch_weather_from_api(city: str) -> str:
    """实际调用高德天气API，网络异常时自动重试1次"""
    api_key = agent_conf.get("amap_api_key")
    base_url = agent_conf.get("amap_weather_url", "https://restapi.amap.com/v3/weather/weatherInfo")
    url = f"{base_url}?city={requests.utils.quote(city)}&key={api_key}&extensions=base"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()

    if data.get("status") != "1":
        raise RuntimeError(f"API返回错误: {data.get('info', '未知错误')}")

    lives = data.get("lives", [])
    if not lives:
        raise RuntimeError("API未返回天气数据")

    weather_data = lives[0]
    weather_desc = weather_data.get("weather", "晴")
    temp = weather_data.get("temperature", "26")
    humidity = weather_data.get("humidity", "50")
    wind_dir = weather_data.get("winddirection", "南")
    wind_power = weather_data.get("windpower", "1级")
    report_time = weather_data.get("reporttime", "")

    result = f"城市{city}天气为{weather_desc}，气温{temp}°C，空气湿度{humidity}%，{wind_dir}风{wind_power}"
    if report_time:
        result += f"，数据更新时间：{report_time}"
    return result


@tool(description="获取指定城市的天气,以消息字符串的形式返回")
def get_weather(city: str) -> str:
    """调用高德地图天气API获取天气信息，网络异常时自动重试1次"""
    api_key = agent_conf.get("amap_api_key")
    if not api_key:
        logger.warning("未配置AMAP_API_KEY，使用模拟数据")
        return f"城市{city}天气为晴天,气温26摄氏度,空气湿度50%,南风1级,AQI21,最近6小时降雨概率极低"

    try:
        return _fetch_weather_from_api(city)
    except (requests.RequestException, RuntimeError) as e:
        logger.error(f"获取天气失败: {str(e)}")
        return f"获取城市{city}天气信息失败：{str(e)}"


@retry(stop=stop_after_attempt(2), wait=wait_fixed(2), reraise=True)
def _fetch_location_from_api() -> str:
    """实际调用高德IP定位API，网络异常时自动重试1次"""
    api_key = agent_conf.get("amap_api_key")
    base_url = agent_conf.get("amap_ip_location_url", "https://restapi.amap.com/v3/ip")
    url = f"{base_url}?key={api_key}"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()

    if data.get("status") != "1":
        raise RuntimeError(f"API返回错误: {data.get('info', '未知错误')}")

    city = data.get("city", "")
    if not city:
        raise RuntimeError("API未返回城市信息")

    city = city.replace("市", "")
    return city


@tool(description="获取用户所在城市的名称,以纯字符串形式返回")
def get_user_location() -> str:
    """调用高德地图IP定位API获取用户所在城市，网络异常时自动重试1次"""
    api_key = agent_conf.get("amap_api_key")
    if not api_key:
        logger.warning("未配置AMAP_API_KEY，使用模拟数据")
        return random.choice(["深圳", "合肥", "杭州"])

    try:
        city = _fetch_location_from_api()
        logger.info(f"获取用户位置成功: {city}")
        return city
    except (requests.RequestException, RuntimeError) as e:
        logger.error(f"获取位置失败: {str(e)}")
        return random.choice(["深圳", "合肥", "杭州"])


@tool(description="获取当前用户ID")
def get_user_id() -> str:
    return "unknown"


@tool(description="获取当前日期时间")
def get_current_month() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@tool(description="无入参,无返回值,调用后触发中间件自动为生成的场景动态注入上下文信息,为后续提示词切换提供上下文信息")
def fill_context_for_report() -> str:
    return "fill_context_for_report已调用"


def generate_external_data():
    if external_data:  # 已加载过，跳过重复读文件
        return
    external_data_path = get_abs_path(agent_conf["external_data_path"])
    if not os.path.exists(external_data_path):
        raise FileNotFoundError(f"外部数据文件不存在:{external_data_path}")
    with open(external_data_path, "r", encoding="utf-8") as f:
        for line in f.readlines()[1:]:
            arr: list[str] = line.strip().split(",")
            user_id: str = arr[0].replace('"', "")
            feature: str = arr[1].replace('"', "")
            efficiency: str = arr[2].replace('"', "")
            consumables: str = arr[3].replace('"', "")
            comparison: str = arr[4].replace('"', "")
            time: str = arr[5].replace('"', "")
            if user_id not in external_data:
                external_data[user_id] = {}
            external_data[user_id][time] = {
                "特征": feature,
                "效率": efficiency,
                "耗材": consumables,
                "对比": comparison,
            }


@tool(description="从外部系统中获取指定用户在指定月份的使用记录,以纯字符串形式返回,如果未检索到返回空字符串")
def fetch_external_data(user_id: str, month: str) -> str:
    generate_external_data()
    try:
        return external_data[user_id][month]
    except KeyError:
        logger.warning(f"用户{user_id}在{month}月没有使用记录")
        return ""


if __name__ == "__main__":
    # 测试高德天气API
    print("测试天气API:")
    print(get_weather("深圳"))
    
    # 测试IP定位API
    print("\n测试定位API:")
    print(get_user_location())
