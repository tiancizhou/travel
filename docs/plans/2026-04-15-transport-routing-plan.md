# Transport Routing Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add walking, riding, and driving route planning with a unified backend API and frontend mode switcher.

**Architecture:** Extend the existing `/api/plan` flow with a `mode` parameter. The backend dispatches to the matching AMap Web Service route API, normalizes route geometry into the current frontend shape, and passes mode-aware context into guide generation. The frontend adds a transport mode selector and renders the active mode with the route result.

**Tech Stack:** FastAPI, Pydantic, httpx, SQLite, static HTML/CSS/JS, AMap Web Service API

---

### Task 1: Extend Request And Response Models

**Files:**
- Modify: `models/query.py`

**Step 1: Add route mode to request model**

Update `PlanRequest` to include a `mode` field with allowed values for `walking`, `riding`, and `driving`.

**Step 2: Add route mode to response model**

Update `PlanResponse` to return the selected mode so the frontend can display it.

**Step 3: Run syntax verification**

Run: `uv run python -m py_compile models\query.py`
Expected: no output

### Task 2: Add Multi-Mode Route Service Support

**Files:**
- Modify: `services/amap.py`

**Step 1: Add AMap route endpoints**

Define URLs for:

- walking route
- riding route
- driving route

**Step 2: Add per-mode fetchers**

Implement minimal HTTP helpers for riding and driving, matching the existing walking style.

**Step 3: Add per-mode parsers**

Normalize each response into:

- `distance`
- `duration`
- `points`

**Step 4: Add a route dispatcher**

Create a single function that accepts `mode`, `origin`, and `destination`, then routes to the correct API and parser.

**Step 5: Run syntax verification**

Run: `uv run python -m py_compile services\amap.py`
Expected: no output

### Task 3: Make Guide Generation Mode-Aware

**Files:**
- Modify: `services/llm.py`

**Step 1: Add route mode parameter**

Update `generate_city_walk_guide` to accept `mode`.

**Step 2: Add mode-specific copy guidance**

Adjust the prompt so:

- walking uses City Walk tone
- riding emphasizes pace, scenery, and weather
- driving emphasizes efficiency, parking, and stopovers

**Step 3: Keep shared weather and POI context**

Do not change the current POI and weather enrichment flow beyond making the prompt mode-aware.

**Step 4: Run syntax verification**

Run: `uv run python -m py_compile services\llm.py`
Expected: no output

### Task 4: Wire Mode Through The API Layer

**Files:**
- Modify: `main.py`

**Step 1: Read mode from request**

Update `/api/plan` to read the requested route mode.

**Step 2: Use the route dispatcher**

Replace walk-only route fetch logic with the new multi-mode route dispatch function.

**Step 3: Pass mode into guide generation**

Ensure the selected mode is forwarded into the LLM service.

**Step 4: Return mode in response**

Include `mode` in the normalized API response.

**Step 5: Run syntax verification**

Run: `uv run python -m py_compile main.py`
Expected: no output

### Task 5: Add Transport Mode Selector To The Frontend

**Files:**
- Modify: `static/index.html`

**Step 1: Add selector UI**

Add a compact segmented control with three options:

- `步行`
- `骑行`
- `驾车`

Default to `步行`.

**Step 2: Track active mode in frontend state**

Store the selected mode in JavaScript and update the active button styling on click.

**Step 3: Send mode in the plan request**

Include the mode in the `/api/plan` request body.

**Step 4: Show mode in result area**

Render the active mode near route stats so the user can clearly tell which route type is shown.

**Step 5: Preserve existing features**

Keep current search, location, map click selection, weather, and guide rendering intact.

### Task 6: Full Verification

**Files:**
- Verify: `main.py`
- Verify: `models/query.py`
- Verify: `services/amap.py`
- Verify: `services/llm.py`
- Verify: `static/index.html`

**Step 1: Compile Python files**

Run: `uv run python -m py_compile main.py database.py models\query.py services\amap.py services\llm.py run.py`
Expected: no output

**Step 2: Verify app import**

Run: `uv run python -c "import main; print('app import ok')"`
Expected: `app import ok`

**Step 3: Manual verification**

Run the app and verify these flows manually:

- walking route renders
- riding route renders
- driving route renders
- result area shows selected mode
- weather card still renders
- guide text changes appropriately with mode

Run: `uv run run.py dev`
