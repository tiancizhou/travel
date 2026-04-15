import os
import httpx
from dotenv import load_dotenv

load_dotenv()

_guide_cfg: dict = {
    "key":      os.getenv("GUIDE_LLM_KEY",      ""),
    "base_url": os.getenv("GUIDE_LLM_BASE_URL", "https://open.bigmodel.cn/api/anthropic"),
    "model":    os.getenv("GUIDE_LLM_MODEL",    "glm-5.1"),
}
_point_cfg: dict = {
    "key":      os.getenv("POINT_LLM_KEY",      ""),
    "base_url": os.getenv("POINT_LLM_BASE_URL", "https://windhub.cc"),
    "model":    os.getenv("POINT_LLM_MODEL",    "grok-4.20-beta"),
}


def update_guide_cfg(key: str, base_url: str, model: str) -> None:
    if not key or not base_url or not model:
        raise ValueError("key, base_url, and model must all be non-empty strings")
    _guide_cfg.update({"key": key, "base_url": base_url, "model": model})


def update_point_cfg(key: str, base_url: str, model: str) -> None:
    if not key or not base_url or not model:
        raise ValueError("key, base_url, and model must all be non-empty strings")
    _point_cfg.update({"key": key, "base_url": base_url, "model": model})


def get_configs() -> tuple[dict, dict]:
    """Return shallow copies of current guide and point configs."""
    return dict(_guide_cfg), dict(_point_cfg)


import warnings

if not _guide_cfg["key"]:
    warnings.warn("GUIDE_LLM_KEY is not set — route guide generation will fail", RuntimeWarning, stacklevel=1)
if not _point_cfg["key"]:
    warnings.warn("POINT_LLM_KEY is not set — point analysis will fail", RuntimeWarning, stacklevel=1)

CITY_WALK_PROMPT = """你是一位非常务实的本地出行规划助手，请根据真实路线信息生成可执行的路线建议。

出行方式：{mode_label}
起点：{start_name}（{start_coord}）
终点：{end_name}（{end_coord}）
路线距离：{distance}米
预计用时：{duration}分钟

{weather_section}

{landmark_section}

{food_section}

{mode_instruction}

输出要求：
1. 优先给出怎么走、哪里停、为什么停，少写空泛抒情句。
2. 只使用上方真实地点数据中的少量优质点，不要堆砌地点名称。
3. 如果路线较长，必须明确提醒是否适合纯步行。
4. 不要编造未提供的精确换乘线路编号、出入口、站点细节；如果信息不足，就写“建议优先选择直达或少换乘方案”。
5. 不要使用“无脑漫游”“顶流”“超级出片”这类营销口吻。
6. 当前产品只支持“步行”和“公交地铁”两种建议，禁止提及骑行、驾车、自驾等其他模式。
7. “精选停留点”只能从景点地标候选中挑选；“补给建议”只能从补给点候选中挑选，不能混用。
8. 如果是步行模式且路线偏长，要直接建议改用公交地铁，不要鼓励用户硬走完全程。
9. 分析路线时要关注起点附近、中途经过区域、终点周边三个部分，不能只写起点和终点。

请严格按以下格式输出：

## {title}

### 路线判断
用1-2句话判断这条路线更适合半天、一天，是否适合轻松出行。

### 建议走法
按先后顺序说明怎么安排这条路线，2-3条即可。

### 沿线看点分析
简要说明起点附近、中段经过区域、终点周边分别有什么值得关注的地方。

### 精选停留点
只列2-3个真正值得停的点。每个点写：名称、为什么值得停、建议停留多久。

### 补给建议
只列1-2个补给或吃饭建议，强调放在哪一段更合适。

### 注意事项
给2-3条最有用的提醒，优先写天气、步行强度、换乘复杂度或时间安排。

总字数控制在220到380字之间。"""


def _build_mode_prompt(mode: str) -> tuple[str, str]:
    if mode == "transit":
        return (
            "公交地铁",
            "标题用“公交地铁出行建议”。重点说明这条路线不适合纯步行时应如何借助公共交通完成，并突出换乘效率、接驳步行距离和下车后如何安排。",
        )
    return (
        "步行",
        "标题用“City Walk 路线建议”。重点说明步行节奏、先后顺序、在哪些点最值得停留。",
    )


def _build_walk_feasibility(mode: str, distance: int, duration: int) -> str:
    if mode != "walking":
        return ""
    if distance > 7000 or duration > 5400:
        return "这条路线对轻松步行不友好，请在“路线判断”和“注意事项”里明确建议改用公交地铁，不要推荐其他出行方式。"
    return "这条路线仍可作为步行为主的安排，但要提醒用户合理分配体力。"


def _build_title(mode: str) -> str:
    if mode == "transit":
        return "公交地铁出行建议"
    return "City Walk 路线建议"


def _build_landmark_section(route_landmarks: list[dict] | None) -> str:
    if not route_landmarks:
        return "沿线景点地标候选：{waypoints}（未获取到足够可靠的景点数据，请谨慎概括，不要编造具体景点细节）"

    lines = ["沿线景点地标候选（优先用于沿线分析和精选停留点）："]
    for p in route_landmarks:
        dist = p.get("distance", "")
        dist_text = f"距路线{dist}米" if dist else ""
        lines.append(f"- {p['name']}（{p.get('type', '未知类型')}）{dist_text}")
    return "\n".join(lines)


def _build_food_section(route_food_stops: list[dict] | None) -> str:
    if not route_food_stops:
        return "沿线补给点候选：未获取到足够可靠的补给点数据，可以只给补给类型建议。"

    lines = ["沿线补给点候选（只用于补给建议，不可作为主要停留点）："]
    for p in route_food_stops:
        dist = p.get("distance", "")
        dist_text = f"距路线{dist}米" if dist else ""
        lines.append(f"- {p['name']}（{p.get('type', '未知类型')}）{dist_text}")
    return "\n".join(lines)


def _build_weather_section(weather: dict | None) -> str:
    if not weather:
        return ""
    return (
        f"当前天气：{weather.get('city', '')} {weather.get('weather', '')}，"
        f"气温{weather.get('temperature', '')}°C，"
        f"{weather.get('winddirection', '')}风{weather.get('windpower', '')}级，"
        f"湿度{weather.get('humidity', '')}%"
        f"（更新时间：{weather.get('reporttime', '')}）"
    )


async def generate_city_walk_guide(
    mode: str,
    start_name: str,
    start_coord: str,
    end_name: str,
    end_coord: str,
    distance: int,
    duration: int,
    waypoints: list[list[float]],
    route_landmarks: list[dict] | None = None,
    route_food_stops: list[dict] | None = None,
    weather: dict | None = None,
) -> str:
    wp_str = " → ".join(
        [f"({p[0]:.4f},{p[1]:.4f})" for p in waypoints[:: max(1, len(waypoints) // 5)]]
    )

    landmark_section = _build_landmark_section(route_landmarks)
    if "{waypoints}" in landmark_section:
        landmark_section = landmark_section.replace("{waypoints}", wp_str)
    food_section = _build_food_section(route_food_stops)

    weather_section = _build_weather_section(weather)
    mode_label, mode_instruction = _build_mode_prompt(mode)
    title = _build_title(mode)
    walk_feasibility = _build_walk_feasibility(mode, distance, duration)

    prompt = CITY_WALK_PROMPT.format(
        title=title,
        mode_label=mode_label,
        start_name=start_name,
        start_coord=start_coord,
        end_name=end_name,
        end_coord=end_coord,
        distance=distance,
        duration=duration,
        weather_section=weather_section,
        landmark_section=landmark_section,
        food_section=food_section,
        mode_instruction=f"{mode_instruction} {walk_feasibility}",
    )

    cfg = dict(_guide_cfg)  # snapshot — values are all str, shallow copy is safe
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{cfg['base_url']}/v1/messages",
            headers={
                "x-api-key": cfg["key"],
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": cfg["model"],
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=60.0,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"]


POINT_ANALYSIS_PROMPT = """你是一位本地旅行顾问，请只针对一个具体点位做简洁、可信的景点分析。

点位名称：{label}
点位坐标：{lng},{lat}

周边景点候选：
{landmarks}

输出要求：
1. 说明这个点位为什么值得停留，或者为什么只是适合作为经过点。
2. 如果周边有代表性景点，列出2-4个并简述理由。
3. 给出建议停留时长。
4. 不要编造交通线路、营业时间或门票信息。
5. 控制在180到260字。
"""


async def generate_point_analysis(
    label: str,
    lng: float,
    lat: float,
    landmarks: list[dict],
) -> str:
    landmark_lines = (
        "\n".join(
            [
                f"- {p.get('name', '')}（{p.get('type', '未知类型')}）"
                for p in landmarks[:6]
            ]
        )
        or "- 暂无可靠景点候选"
    )

    prompt = POINT_ANALYSIS_PROMPT.format(
        label=label,
        lng=lng,
        lat=lat,
        landmarks=landmark_lines,
    )

    cfg = dict(_point_cfg)  # snapshot — values are all str, shallow copy is safe
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{cfg['base_url']}/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {cfg['key']}",
                "Content-Type": "application/json",
            },
            json={
                "model": cfg["model"],
                "max_tokens": 512,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=60.0,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
