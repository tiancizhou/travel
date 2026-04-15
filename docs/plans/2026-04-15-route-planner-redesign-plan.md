# Route Planner Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform the current app into a waypoint-based route planner with per-point AI analysis.

**Architecture:** Split the product into two concerns: route building and point analysis. Route building uses start, waypoints, and end to draw the route. Point analysis is triggered on marker click and returns a focused AI summary for that point only.

**Tech Stack:** FastAPI, Pydantic, httpx, static HTML/CSS/JS, AMap Web Service API, LLM prompt generation

---

### Task 1: Extend Route Request Model For Waypoints

**Files:**
- Modify: `models/query.py`

**Step 1: Add waypoint model**

Define a coordinate model for route waypoints.

**Step 2: Update plan request**

Allow `/api/plan` to accept an ordered waypoint list.

### Task 2: Update Backend Route Planning To Use Waypoints

**Files:**
- Modify: `services/amap.py`
- Modify: `main.py`

**Step 1: Pass waypoint list into route planning**

Support route planning based on start, waypoints, and end.

**Step 2: Keep response focused on route geometry and summary**

Remove dependency on full-route guide generation for primary route output.

### Task 3: Add Point Analysis Endpoint

**Files:**
- Modify: `models/query.py`
- Modify: `main.py`
- Modify: `services/llm.py`
- Modify: `services/amap.py`

**Step 1: Add point-analysis request and response models**

Define a simple request using point coordinates and an optional label.

**Step 2: Add nearby landmark lookup for a single point**

Search nearby scenic/cultural POIs around the selected point.

**Step 3: Add point-analysis prompt**

Generate a concise local analysis for one point, not for the entire route.

**Step 4: Expose `/api/analyze-point`**

Return reverse-geocoded name, nearby points of interest, and AI analysis.

### Task 4: Redesign Frontend For Waypoints

**Files:**
- Modify: `static/index.html`

**Step 1: Change click workflow**

First click sets start, second click sets end, subsequent clicks append waypoints.

**Step 2: Show ordered point list**

Render start, waypoint list, and end in the right panel.

**Step 3: Add remove control for each waypoint**

Allow deleting a waypoint without resetting everything.

**Step 4: Update route submission**

Send start, waypoint list, and end to `/api/plan`.

### Task 5: Add Marker-Based Point Analysis UI

**Files:**
- Modify: `static/index.html`

**Step 1: Make route markers clickable**

Clicking a marker should request AI analysis for that point.

**Step 2: Render point analysis in a dedicated panel or modal**

Show address, nearby highlights, and the point-specific analysis.

### Task 6: Verify Syntax And Import

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
