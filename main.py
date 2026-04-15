from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from database import init_db, insert_query, get_history
from models.query import (
    PlanRequest,
    PlanResponse,
    PointAnalysisRequest,
    PointAnalysisResponse,
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
from services.llm import generate_city_walk_guide, generate_point_analysis


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

    try:
        analysis = await generate_point_analysis(
            label=req.label or name,
            lng=req.lng,
            lat=req.lat,
            landmarks=landmarks,
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
