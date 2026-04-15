from typing import Literal

from pydantic import BaseModel, field_validator


class Waypoint(BaseModel):
    lng: float
    lat: float
    label: str = ""


class PlanRequest(BaseModel):
    start_lng: float
    start_lat: float
    end_lng: float
    end_lat: float
    mode: Literal["walking", "transit"] = "walking"
    waypoints: list[Waypoint] = []


class WeatherInfo(BaseModel):
    province: str = ""
    city: str = ""
    weather: str = ""
    temperature: str = ""
    winddirection: str = ""
    windpower: str = ""
    humidity: str = ""
    reporttime: str = ""


class PlanResponse(BaseModel):
    distance: int
    duration: int
    route: list[list[float]]
    guide: str = ""
    mode: Literal["walking", "transit"] = "walking"
    weather: WeatherInfo | None = None
    transit_summary: str | None = None
    transit_steps: list[str] | None = None


class PointAnalysisRequest(BaseModel):
    lng: float
    lat: float
    label: str = ""


class PointAnalysisResponse(BaseModel):
    name: str
    analysis: str
    nearby_landmarks: list[str]


class HistoryItem(BaseModel):
    id: int
    created_at: str
    start_lng: float
    start_lat: float
    end_lng: float
    end_lat: float
    distance: int | None = None
    duration: int | None = None
    guide: str | None = None


class LLMProviderConfig(BaseModel):
    key: str
    base_url: str
    model: str

    @field_validator("base_url", "model")
    @classmethod
    def must_be_non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be empty")
        return v


class ConfigRequest(BaseModel):
    guide: LLMProviderConfig
    point: LLMProviderConfig


class MaskedProviderConfig(BaseModel):
    key: str        # masked (first 8 chars + ***)
    base_url: str
    model: str


class ConfigResponse(BaseModel):
    ok: bool
    guide: MaskedProviderConfig
    point: MaskedProviderConfig
