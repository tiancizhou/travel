from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from database import init_db, insert_query, get_history
from models.query import (
    PlanRequest,
    PlanResponse,
    PointAnalysisRequest,
    PointAnalysisResponse,
    ConfigRequest,
    ConfigResponse,
    MaskedProviderConfig,
)
from services.amap import (
    get_route,
    get_route_with_waypoints,
    reverse_geocode,
    analyze_point_context,
    get_adcode,
    search_poi,
    search_around_poi,
    search_route_pois,
    search_destination_landmarks,
    get_weather,
    ip_locate,
)
from services.llm import (
    generate_city_walk_guide,
    generate_point_research,
    generate_point_analysis,
    update_guide_cfg,
    update_point_cfg,
    get_configs,
)



def _mask_key(key: str) -> str:
    """Return first 8 chars + '***', or '***' if key is shorter than 8 chars."""
    if not key:
        return ""
    return key[:8] + "***" if len(key) >= 8 else "***"


def _write_env_vars(updates: dict[str, str]) -> None:
    """Overwrite specific key=value lines in .env; append any keys not already present."""
    env_path = Path(".env")
    lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    written: set[str] = set()
    new_lines: list[str] = []
    for line in lines:
        if "=" not in line or line.lstrip().startswith("#"):
            new_lines.append(line)
            continue
        key = line.split("=", 1)[0].strip()
        if key in updates:
            new_lines.append(f"{key}={updates[key]}")
            written.add(key)
        else:
            new_lines.append(line)
    for key, value in updates.items():
        if key not in written:
            new_lines.append(f"{key}={value}")
    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="City Walk 旅游助手", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def index():
    return FileResponse("static/index.html")


@app.post("/api/plan", response_model=PlanResponse)
async def create_plan(req: PlanRequest):
    origin = f"{req.start_lng},{req.start_lat}"
    destination = f"{req.end_lng},{req.end_lat}"
    waypoint_strings = [f"{pt.lng},{pt.lat}" for pt in req.waypoints]
    transit_summary = None
    transit_steps = None
    adcode = ""

    try:
        adcode = await get_adcode(req.start_lng, req.start_lat)
    except Exception:
        adcode = ""

    try:
        (
            distance,
            duration,
            points,
            transit_summary,
            transit_steps,
        ) = await get_route_with_waypoints(
            req.mode,
            origin,
            destination,
            waypoint_strings,
            city=adcode,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    try:
        start_name = await reverse_geocode(req.start_lng, req.start_lat)
        end_name = await reverse_geocode(req.end_lng, req.end_lat)
    except Exception:
        start_name = "起点"
        end_name = "终点"

    await insert_query(
        req.start_lng,
        req.start_lat,
        req.end_lng,
        req.end_lat,
        distance,
        duration,
        "",
    )

    return PlanResponse(
        distance=distance,
        duration=duration,
        route=points,
        guide="",
        mode=req.mode,
        weather=None,
        transit_summary=transit_summary,
        transit_steps=transit_steps,
    )


@app.post("/api/analyze-point", response_model=PointAnalysisResponse)
async def analyze_point(req: PointAnalysisRequest):
    try:
        name, landmarks = await analyze_point_context(req.lng, req.lat)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    label = req.label or name

    # 第一阶段：Grok 搜索提炼（失败则降级为 None）
    research = await generate_point_research(label=label, lng=req.lng, lat=req.lat)

    # 第二阶段：GLM 分析总结（有 research 则用增强版 prompt，否则用 fallback）
    try:
        analysis = await generate_point_analysis(
            label=label,
            lng=req.lng,
            lat=req.lat,
            landmarks=landmarks,
            research=research,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"点位分析生成失败: {str(e)}")

    return PointAnalysisResponse(
        name=name,
        analysis=analysis,
        nearby_landmarks=[p.get("name", "") for p in landmarks[:6] if p.get("name")],
    )


@app.get("/api/search")
async def search(
    keywords: str,
    city: str = "",
    location: str = "",
    offset: int = 10,
):
    if not keywords:
        return []
    results = await search_poi(keywords, city=city, location=location, offset=offset)
    return results


@app.get("/api/search/nearby")
async def search_nearby(
    location: str,
    keywords: str = "",
    radius: int = 1500,
    offset: int = 10,
):
    if not location:
        return []
    safe_radius = min(max(radius, 100), 3000)
    results = await search_around_poi(
        location=location,
        keywords=keywords,
        radius=safe_radius,
        offset=offset,
    )
    return results


@app.get("/api/location")
async def locate(request: Request):
    ip = request.client.host if request.client else ""
    result = await ip_locate(ip)
    if not result:
        return {"lng": 116.397428, "lat": 39.90923, "city": "北京"}
    return result


@app.get("/api/history")
async def history(limit: int = 20):
    return await get_history(limit)


def _config_response() -> ConfigResponse:
    """Build a ConfigResponse from the current live LLM configs with masked keys."""
    guide_cfg, point_cfg = get_configs()
    return ConfigResponse(
        ok=True,
        guide=MaskedProviderConfig(
            key=_mask_key(guide_cfg["key"]),
            base_url=guide_cfg["base_url"],
            model=guide_cfg["model"],
        ),
        point=MaskedProviderConfig(
            key=_mask_key(point_cfg["key"]),
            base_url=point_cfg["base_url"],
            model=point_cfg["model"],
        ),
    )


@app.get("/api/config", response_model=ConfigResponse)
async def get_config():
    return _config_response()


@app.post("/api/config", response_model=ConfigResponse)
async def set_config(req: ConfigRequest):
    guide_cfg, point_cfg = get_configs()

    # Empty string = user did not modify the key; keep existing value
    guide_key = req.guide.key if req.guide.key else guide_cfg["key"]
    point_key = req.point.key if req.point.key else point_cfg["key"]

    # Hot-update in-memory config (base_url/model validated non-empty by Pydantic)
    update_guide_cfg(guide_key, req.guide.base_url, req.guide.model)
    update_point_cfg(point_key, req.point.base_url, req.point.model)

    # Write back to .env (key only written when user provided a new one)
    env_updates: dict[str, str] = {
        "GUIDE_LLM_BASE_URL": req.guide.base_url,
        "GUIDE_LLM_MODEL":    req.guide.model,
        "POINT_LLM_BASE_URL": req.point.base_url,
        "POINT_LLM_MODEL":    req.point.model,
    }
    if req.guide.key:
        env_updates["GUIDE_LLM_KEY"] = req.guide.key
    if req.point.key:
        env_updates["POINT_LLM_KEY"] = req.point.key
    _write_env_vars(env_updates)

    # Return current state (second get_configs() call is safe — no await between updates above)
    return _config_response()
