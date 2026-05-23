"""
高德地图路线规划模块
为行程中相邻景点间提供实际交通方案（时长、方式、提示）
"""

import os
import requests
from typing import Any, Dict, Optional, Tuple

AMAP_BASE_URL = "https://restapi.amap.com/v3"
_REQUEST_TIMEOUT = 5  # seconds


def _get_api_key() -> Optional[str]:
    return os.getenv("AMAP_API_KEY")


def geocode(address: str, city: str = "") -> Optional[Tuple[float, float]]:
    """将地址/景点名转换为高德坐标 (lng, lat)，失败返回 None。"""
    key = _get_api_key()
    if not key:
        return None

    params: Dict[str, str] = {"address": address, "key": key}
    if city:
        params["city"] = city

    try:
        resp = requests.get(
            f"{AMAP_BASE_URL}/geocode/geo", params=params, timeout=_REQUEST_TIMEOUT
        )
        data = resp.json()
        if data.get("status") == "1" and data.get("geocodes"):
            lng_str, lat_str = data["geocodes"][0]["location"].split(",")
            return float(lng_str), float(lat_str)
    except Exception:
        pass
    return None


def _transit_segment(
    origin: str, destination: str, city: str, key: str
) -> Optional[Dict[str, Any]]:
    """尝试获取公共交通方案，失败返回 None。"""
    try:
        resp = requests.get(
            f"{AMAP_BASE_URL}/direction/transit/integrated",
            params={
                "origin": origin,
                "destination": destination,
                "city": city or "全国",
                "key": key,
            },
            timeout=_REQUEST_TIMEOUT,
        )
        data = resp.json()
        transits = data.get("route", {}).get("transits") or []
        if data.get("status") != "1" or not transits:
            return None

        transit = transits[0]
        duration_min = max(1, int(transit.get("duration", 60)) // 60)

        modes: list[str] = []
        stop_tips: list[str] = []
        for seg in transit.get("segments", []):
            buslines = seg.get("bus", {}).get("buslines") or []
            walking = seg.get("walking", {})
            if buslines:
                line = buslines[0]
                modes.append(line.get("name", "公共交通"))
                dep = (line.get("departure_stop") or {}).get("name", "")
                arr = (line.get("arrival_stop") or {}).get("name", "")
                if dep and arr:
                    stop_tips.append(f"{dep}上车，{arr}下车")
            elif int(walking.get("distance", 0)) > 100:
                modes.append(f"步行{int(walking['distance'])}米")

        mode_label = " → ".join(modes) if modes else "公共交通"
        tip_detail = "；".join(stop_tips)
        tip = f"约{duration_min}分钟。{tip_detail}" if tip_detail else f"约{duration_min}分钟"

        return {"duration_min": duration_min, "mode": mode_label, "tip": tip}
    except Exception:
        return None


def _driving_segment(origin: str, destination: str, key: str) -> Dict[str, Any]:
    """获取驾车方案，任何错误时返回默认估计值。"""
    try:
        resp = requests.get(
            f"{AMAP_BASE_URL}/direction/driving",
            params={"origin": origin, "destination": destination, "key": key},
            timeout=_REQUEST_TIMEOUT,
        )
        data = resp.json()
        paths = data.get("route", {}).get("paths") or []
        if data.get("status") == "1" and paths:
            path = paths[0]
            duration_min = max(1, int(path.get("duration", 1800)) // 60)
            km = int(path.get("distance", 0)) // 1000
            return {
                "duration_min": duration_min,
                "mode": "打车/自驾",
                "tip": f"约{duration_min}分钟，路程约{km}公里",
            }
    except Exception:
        pass
    return {"duration_min": 30, "mode": "出行", "tip": "建议提前查询路线"}


def get_travel_segment(
    origin: Tuple[float, float],
    destination: Tuple[float, float],
    city: str = "",
) -> Dict[str, Any]:
    """
    获取两个坐标点间的推荐交通方案。
    优先尝试公共交通，不可用时降级到驾车。
    """
    key = _get_api_key()
    if not key:
        return {}

    origin_str = f"{origin[0]},{origin[1]}"
    dest_str = f"{destination[0]},{destination[1]}"

    result = _transit_segment(origin_str, dest_str, city, key)
    if result:
        return result
    return _driving_segment(origin_str, dest_str, key)


def enrich_itinerary_with_traffic(
    itinerary: Dict[str, Any], destination: str
) -> Dict[str, Any]:
    """
    为行程每天的相邻时间段（上午→下午、下午→晚上）注入实际交通信息。
    若 AMAP_API_KEY 未配置或请求失败，静默跳过，不影响原行程。
    """
    if not _get_api_key():
        return itinerary

    for day in itinerary.get("itinerary") or []:
        for from_slot, to_slot, travel_key in (
            ("morning", "afternoon", "travel_to_afternoon"),
            ("afternoon", "evening", "travel_to_evening"),
        ):
            from_spot = (day.get(from_slot) or {}).get("spot", "")
            to_spot = (day.get(to_slot) or {}).get("spot", "")
            if not from_spot or not to_spot:
                continue

            # Geocode with destination city as hint for accuracy
            from_coords = geocode(f"{destination} {from_spot}", destination)
            to_coords = geocode(f"{destination} {to_spot}", destination)
            if not from_coords or not to_coords:
                continue

            segment = get_travel_segment(from_coords, to_coords, destination)
            if segment:
                day[travel_key] = segment

    return itinerary
