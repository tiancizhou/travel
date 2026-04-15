# Transport Routing Design

## Goal

Extend the current travel planner from a walk-only City Walk flow to support three route modes: walking, riding, and driving.

## Chosen Approach

Use a backend-unified routing model.

- Frontend adds a mode switcher for `walking`, `riding`, and `driving`
- Frontend sends the selected mode to `/api/plan`
- Backend calls the corresponding AMap Web Service API
- Backend normalizes route output into the existing response shape used by the map UI
- LLM prompt receives the selected mode so the guide text matches the transport choice

This keeps route logic centralized and makes later expansion to transit easier.

## API Design

### Request

`PlanRequest` gains a `mode` field.

Allowed values:

- `walking`
- `riding`
- `driving`

Default remains `walking` for compatibility.

### Response

Keep the existing normalized shape:

- `distance`
- `duration`
- `route`
- `guide`
- `weather`

Add `mode` so the frontend can render the current transport type explicitly.

## Backend Changes

### AMap Service

Add support for:

- walking route API
- riding route API
- driving route API

Create a route dispatcher based on mode and normalize the returned polyline data.

Because the AMap response structures differ slightly between modes, parsing should be mode-specific but converge into a common tuple:

- distance in meters
- duration in seconds
- route point list as `list[list[float]]`

### Guide Generation

Pass route mode into the LLM prompt.

- `walking`: City Walk tone, local exploration, slow travel
- `riding`: scenery, rhythm, rest points, weather sensitivity
- `driving`: parking, quick stop points, efficient detours

POI and weather enrichment remain shared across all modes.

## Frontend Changes

Add a compact three-mode selector in the sidebar.

- `步行`
- `骑行`
- `驾车`

The selected mode is sent in the plan request.

The result area should show the active mode near route stats so the user can tell which route is being rendered.

## Data and Storage

Current SQLite history can remain unchanged for now.

Mode is useful for analytics and history replay, but it is not required for the first iteration. If history becomes more important, a migration can add a `mode` column later.

## Risks

- Driving and riding API responses may not match walking field structure exactly
- Some route modes may produce sparse points, affecting POI sampling quality
- Guide copy must stay coherent across transport modes

## Verification

Verify with:

- Python syntax compilation
- FastAPI app import
- Manual route generation for walking, riding, and driving
- Confirm map polyline renders for all three modes
- Confirm guide text changes with mode selection
