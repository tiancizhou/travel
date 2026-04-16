import os
import httpx
from dotenv import load_dotenv

load_dotenv()

AMAP_API_KEY = os.getenv("AMAP_API_KEY", "")
WALKING_URL = "https://restapi.amap.com/v3/direction/walking"
TRANSIT_URL = "https://restapi.amap.com/v3/direction/transit/integrated"
GEOCODE_URL = "https://restapi.amap.com/v3/geocode/regeo"
POI_TEXT_URL = "https://restapi.amap.com/v3/place/text"
POI_AROUND_URL = "https://restapi.amap.com/v3/place/around"
WEATHER_URL = "https://restapi.amap.com/v3/weather/weatherInfo"
IP_URL = "https://restapi.amap.com/v3/ip"
GEOCODE_FWD_URL = "https://restapi.amap.com/v3/geocode/geo"


def _route_error_message(mode: str, data: dict) -> str:
    info = data.get("info") or data.get("errmsg") or "未知错误"
    infocode = str(data.get("infocode") or data.get("errcode") or "")

    if (
        infocode in {"10021", "CUQPS_HAS_EXCEEDED_THE_LIMIT"}
        or info == "CUQPS_HAS_EXCEEDED_THE_LIMIT"
    ):
        return (
            "高德接口请求过于频繁，当前已被限流。请稍等几秒后重试，或减少途经点数量。"
        )

    if infocode == "20803" or info == "OVER_DIRECTION_RANGE":
        if mode == "walking":
            return "步行路线距离过长，超出高德步行规划范围。请改用公交地铁模式。"
        if mode == "transit":
            return (
                "公交地铁路线距离过长或当前区域不支持公交换乘规划，请缩短距离后重试。"
            )
        return "路线距离过长，超出当前规划范围。请缩短起终点距离后重试。"

    if mode == "walking":
        return f"高德步行规划失败: {info}"
    if mode == "transit":
        return f"高德公交地铁规划失败: {info}"
    return f"高德路径规划失败: {info}"


async def get_walking_route(origin: str, destination: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            WALKING_URL,
            params={
                "key": AMAP_API_KEY,
                "origin": origin,
                "destination": destination,
            },
        )
        data = resp.json()
        if data.get("status") != "1":
            raise Exception(_route_error_message("walking", data))
        return data


async def get_transit_route(origin: str, destination: str, city: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            TRANSIT_URL,
            params={
                "key": AMAP_API_KEY,
                "origin": origin,
                "destination": destination,
                "city": city,
                "cityd": city,
                "strategy": 0,
            },
        )
        data = resp.json()
        if data.get("status") != "1":
            raise Exception(_route_error_message("transit", data))
        return data


async def reverse_geocode(lng: float, lat: float) -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            GEOCODE_URL,
            params={
                "key": AMAP_API_KEY,
                "location": f"{lng},{lat}",
            },
        )
        data = resp.json()
        if data.get("status") == "1":
            return data.get("regeocode", {}).get("formatted_address", "未知地点")
        return "未知地点"


def parse_route(data: dict) -> tuple[int, int, list[list[float]]]:
    path = data["route"]["paths"][0]
    distance = int(path["distance"])
    duration = int(path["duration"])

    points = []
    for step in path["steps"]:
        polyline = step.get("polyline", "")
        for seg in polyline.split(";"):
            parts = seg.split(",")
            if len(parts) == 2:
                points.append([float(parts[0]), float(parts[1])])

    return distance, duration, points


def parse_transit_route(
    data: dict,
) -> tuple[int, int, list[list[float]], str | None, list[str] | None]:
    transits = data.get("route", {}).get("transits", [])
    if not transits:
        return 0, 0, [], None, None

    transit = transits[0]
    distance = int(transit.get("distance", 0))
    duration = int(transit.get("duration", 0))
    points: list[list[float]] = []
    summary_parts: list[str] = []
    steps_summary: list[str] = []

    for segment in transit.get("segments", []):
        walking = segment.get("walking") or {}
        walking_distance = int(walking.get("distance", 0) or 0)
        if walking_distance > 0:
            steps_summary.append(f"步行约{walking_distance}米")
        for step in walking.get("steps", []):
            polyline = step.get("polyline", "")
            for seg in polyline.split(";"):
                parts = seg.split(",")
                if len(parts) == 2:
                    points.append([float(parts[0]), float(parts[1])])

        bus = segment.get("bus") or {}
        buslines = bus.get("buslines", [])
        for line in buslines:
            name = line.get("name", "公交线路")
            via_num = line.get("via_num", "")
            departure_stop = (line.get("departure_stop") or {}).get("name", "")
            arrival_stop = (line.get("arrival_stop") or {}).get("name", "")
            polyline = line.get("polyline", "")
            if via_num and int(via_num) > 0:
                summary_parts.append(f"{name} {via_num}站")
                detail = f"乘坐{name}，经过{via_num}站"
            else:
                summary_parts.append(name)
                detail = f"乘坐{name}"
            if departure_stop and arrival_stop:
                detail = f"从{departure_stop}上车，{arrival_stop}下车，{detail}"
            elif departure_stop:
                detail = f"从{departure_stop}上车，{detail}"
            steps_summary.append(detail)
            for seg in polyline.split(";"):
                parts = seg.split(",")
                if len(parts) == 2:
                    points.append([float(parts[0]), float(parts[1])])

        railway = segment.get("railway") or {}
        if railway.get("name"):
            summary_parts.append(railway.get("name", "铁路"))
            departure_stop = (railway.get("departure_stop") or {}).get("name", "")
            arrival_stop = (railway.get("arrival_stop") or {}).get("name", "")
            line_name = railway.get("name", "铁路")
            if departure_stop and arrival_stop:
                steps_summary.append(
                    f"乘坐{line_name}，从{departure_stop}到{arrival_stop}"
                )
            else:
                steps_summary.append(f"乘坐{line_name}")
            # 优先使用 polyline（沿线坐标串），退而取 via_stops 离散站点
            railway_polyline = railway.get("polyline", "")
            if railway_polyline:
                for seg in railway_polyline.split(";"):
                    parts = seg.split(",")
                    if len(parts) == 2:
                        points.append([float(parts[0]), float(parts[1])])
            else:
                for stop in railway.get("via_stops", []):
                    location = stop.get("location", "")
                    parts = location.split(",")
                    if len(parts) == 2:
                        points.append([float(parts[0]), float(parts[1])])

    summary = " -> ".join(summary_parts[:4]) if summary_parts else None
    return distance, duration, points, summary, steps_summary or None


async def get_route(
    mode: str,
    origin: str,
    destination: str,
    city: str = "",
) -> tuple[int, int, list[list[float]], str | None, list[str] | None]:
    if mode == "transit":
        data = await get_transit_route(origin, destination, city)
        return parse_transit_route(data)

    data = await get_walking_route(origin, destination)
    distance, duration, points = parse_route(data)
    return distance, duration, points, None, None


async def get_route_with_waypoints(
    mode: str,
    origin: str,
    destination: str,
    waypoints: list[str],
    city: str = "",
) -> tuple[int, int, list[list[float]], str | None, list[str] | None]:
    if not waypoints:
        return await get_route(mode, origin, destination, city)

    total_distance = 0
    total_duration = 0
    merged_points: list[list[float]] = []
    transit_steps: list[str] = []
    transit_summary_parts: list[str] = []

    segments = [origin, *waypoints, destination]
    for idx in range(len(segments) - 1):
        distance, duration, points, summary, steps = await get_route(
            mode,
            segments[idx],
            segments[idx + 1],
            city,
        )
        total_distance += distance
        total_duration += duration
        if merged_points and points:
            merged_points.extend(points[1:])
        else:
            merged_points.extend(points)
        if summary:
            transit_summary_parts.append(summary)
        if steps:
            transit_steps.append(f"第{idx + 1}段")
            transit_steps.extend(steps)

    summary = " | ".join(transit_summary_parts[:3]) if transit_summary_parts else None
    return total_distance, total_duration, merged_points, summary, transit_steps or None


async def analyze_point_context(lng: float, lat: float) -> tuple[str, list[dict]]:
    name = await reverse_geocode(lng, lat)
    scenic_types = "110200|110100|141200|100100|140100|050100|080100|080500|080600|140200|140201|140300"
    nearby = await search_around_poi(
        location=f"{lng},{lat}",
        types=scenic_types,
        radius=1200,
        offset=8,
    )
    split = split_route_pois(nearby)
    return name, split.get("landmarks", [])


async def search_poi(
    keywords: str,
    city: str = "",
    location: str = "",
    offset: int = 10,
    page: int = 1,
) -> list[dict]:
    params = {
        "key": AMAP_API_KEY,
        "keywords": keywords,
        "offset": offset,
        "page": page,
        "output": "JSON",
    }
    if city:
        params["city"] = city
    if location:
        params["location"] = location

    async with httpx.AsyncClient() as client:
        resp = await client.get(POI_TEXT_URL, params=params)
        data = resp.json()
        if data.get("status") != "1":
            return []
        pois = data.get("pois", [])
        return [
            {
                "name": p.get("name", ""),
                "address": p.get("address", ""),
                "location": p.get("location", ""),
                "type": p.get("type", ""),
                "tel": p.get("tel", ""),
            }
            for p in pois
        ]


async def search_around_poi(
    location: str,
    keywords: str = "",
    types: str = "",
    radius: int = 1000,
    offset: int = 10,
) -> list[dict]:
    params = {
        "key": AMAP_API_KEY,
        "location": location,
        "radius": radius,
        "offset": offset,
        "output": "JSON",
    }
    if keywords:
        params["keywords"] = keywords
    if types:
        params["types"] = types

    async with httpx.AsyncClient() as client:
        resp = await client.get(POI_AROUND_URL, params=params)
        data = resp.json()
        if data.get("status") != "1":
            return []
        pois = data.get("pois", [])
        return [
            {
                "name": p.get("name", ""),
                "address": p.get("address", ""),
                "location": p.get("location", ""),
                "type": p.get("type", ""),
                "distance": p.get("distance", ""),
                "tel": p.get("tel", ""),
            }
            for p in pois
        ]


async def search_route_pois(
    waypoints: list[list[float]],
    sample_count: int = 9,
    radius: int = 1000,
) -> dict:
    if not waypoints:
        return []

    step = max(1, len(waypoints) // sample_count)
    sampled = waypoints[::step][:sample_count]

    all_pois: list[dict] = []
    seen: set[str] = set()

    scenic_types = "110200|110100|141200|100100|140100|050100|080100|080500|080600|140200|140201|140300"

    for pt in sampled:
        loc = f"{pt[0]},{pt[1]}"
        pois = await search_around_poi(
            location=loc,
            types=scenic_types,
            radius=radius,
            offset=8,
        )
        for p in pois:
            if p["name"] not in seen:
                seen.add(p["name"])
                all_pois.append(p)

    all_pois.sort(key=lambda p: int(p.get("distance", "99999")))
    return split_route_pois(all_pois)


async def search_destination_landmarks(
    lng: float,
    lat: float,
    destination_name: str,
    radius: int = 1500,
) -> list[dict]:
    scenic_markers = [
        "景区",
        "风景区",
        "名胜",
        "公园",
        "博物院",
        "博物馆",
        "陵",
        "城墙",
    ]
    if not any(marker in destination_name for marker in scenic_markers):
        return []

    scenic_types = "110200|110100|141200|100100|140100|050100|080100|080500|080600|140200|140201|140300"
    pois = await search_around_poi(
        location=f"{lng},{lat}",
        types=scenic_types,
        radius=radius,
        offset=10,
    )

    keyword_results: list[dict] = []
    keyword_candidates = [destination_name, f"{destination_name} 景点"]
    if "钟山" in destination_name or "钟山风景" in destination_name:
        keyword_candidates.extend(["中山陵", "明孝陵", "音乐台", "灵谷寺"])
    if "城墙" in destination_name:
        keyword_candidates.extend(["明城墙", "城墙景区"])
    if "博物院" in destination_name or "博物馆" in destination_name:
        keyword_candidates.extend(
            [destination_name.replace("风景名胜区", ""), "博物院 景点"]
        )

    for keyword in keyword_candidates:
        keyword_pois = await search_poi(keyword, location=f"{lng},{lat}", offset=6)
        keyword_results.extend(keyword_pois)

    merged: list[dict] = []
    seen: set[str] = set()
    for poi in pois + keyword_results:
        name = poi.get("name", "")
        if not name or name in seen or destination_name == name:
            continue
        seen.add(name)
        merged.append(poi)
    return merged


def split_route_pois(pois: list[dict]) -> dict:
    blocked_keywords = [
        "社区",
        "公寓",
        "写字楼",
        "广场",
        "大厦",
        "中心",
        "工业",
        "宿舍",
        "停车场",
        "门诊",
        "医院",
        "酒店",
        "宾馆",
        "炸鸡",
        "烤吧",
        "酒吧",
        "KTV",
        "足疗",
        "网吧",
        "快餐",
        "便利店",
        "肯德基",
        "麦当劳",
        "汉堡",
        "乡村基",
        "露营",
        "棋牌",
        "餐厅",
        "饭店",
        "酒家",
        "小吃",
        "面馆",
        "民宿",
    ]
    scenic_keywords = [
        "景区",
        "公园",
        "博物馆",
        "纪念馆",
        "历史",
        "文化",
        "湖",
        "山",
        "寺",
        "街区",
        "陵",
        "城墙",
        "故居",
        "遗址",
        "牌坊",
    ]
    food_keywords = [
        "鸭血粉丝",
        "小吃",
        "面",
        "汤",
        "咖啡",
        "茶",
        "餐厅",
        "饭店",
        "酒家",
    ]

    scenic: list[dict] = []
    food: list[dict] = []

    for poi in pois:
        name = poi.get("name", "")
        poi_type = poi.get("type", "")
        if not name:
            continue
        if any(word in name for word in blocked_keywords):
            continue

        haystack = f"{name} {poi_type}"
        if any(word in haystack for word in scenic_keywords):
            scenic.append(poi)
            continue
        if any(word in haystack for word in food_keywords):
            food.append(poi)

    scenic = scenic[:8]
    food = food[:2]
    if not scenic:
        fallback_scenic: list[dict] = []
        for poi in pois:
            haystack = f"{poi.get('name', '')} {poi.get('type', '')}"
            if any(word in haystack for word in scenic_keywords):
                fallback_scenic.append(poi)
        scenic = fallback_scenic[:6]
    return {"landmarks": scenic, "food_stops": food}


async def get_weather(adcode: str) -> dict | None:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            WEATHER_URL,
            params={
                "key": AMAP_API_KEY,
                "city": adcode,
                "extensions": "base",
            },
        )
        data = resp.json()
        if data.get("status") == "1" and data.get("lives"):
            live = data["lives"][0]
            return {
                "province": live.get("province", ""),
                "city": live.get("city", ""),
                "weather": live.get("weather", ""),
                "temperature": live.get("temperature", ""),
                "winddirection": live.get("winddirection", ""),
                "windpower": live.get("windpower", ""),
                "humidity": live.get("humidity", ""),
                "reporttime": live.get("reporttime", ""),
            }
    return None


async def get_adcode(lng: float, lat: float) -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            GEOCODE_URL,
            params={
                "key": AMAP_API_KEY,
                "location": f"{lng},{lat}",
                "extensions": "base",
            },
        )
        data = resp.json()
        if data.get("status") == "1":
            ac = data.get("regeocode", {}).get("addressComponent", {}).get("adcode", "")
            if ac:
                return ac
    return ""


async def ip_locate(ip: str = "") -> dict | None:
    params = {"key": AMAP_API_KEY, "output": "JSON"}
    if ip:
        params["ip"] = ip

    async with httpx.AsyncClient() as client:
        resp = await client.get(IP_URL, params=params)
        data = resp.json()
        if data.get("status") == "1" and data.get("rectangle"):
            rect = data["rectangle"]
            parts = rect.split(";")
            if len(parts) == 2:
                lng1, lat1 = parts[0].split(",")
                lng2, lat2 = parts[1].split(",")
                center_lng = (float(lng1) + float(lng2)) / 2
                center_lat = (float(lat1) + float(lat2)) / 2
                return {
                    "lng": round(center_lng, 6),
                    "lat": round(center_lat, 6),
                    "province": data.get("province", ""),
                    "city": data.get("city", ""),
                    "adcode": data.get("adcode", ""),
                }
    return None
