# Along-Route Enrichment Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Improve route POI enrichment so guides analyze important locations across the whole route corridor, including mid-route landmarks.

**Architecture:** Keep the current route-planning pipeline, but enrich the POI collection stage by increasing sample density, broadening scenic/cultural POI coverage, and passing a larger but still filtered set of route-adjacent landmarks into the LLM.

**Tech Stack:** FastAPI, Pydantic, httpx, AMap Web Service API, LLM prompt generation

---

### Task 1: Increase Route Sampling Density

**Files:**
- Modify: `services/amap.py`

**Step 1: Increase sample count**

Collect more sample points along the route so mid-route areas are covered better.

**Step 2: Spread samples evenly**

Ensure samples cover the route corridor, not just the origin and destination vicinity.

### Task 2: Expand Scenic And Cultural Search Coverage

**Files:**
- Modify: `services/amap.py`

**Step 1: Expand scenic type coverage**

Keep focus on scenic, cultural, historic, museum, and park locations.

**Step 2: Increase search radius**

Use a wider nearby search radius so route-adjacent landmarks are less likely to be missed.

### Task 3: Adjust Prompt To Analyze Route Corridor

**Files:**
- Modify: `services/llm.py`

**Step 1: Encourage corridor analysis**

Ask the model to think in three route parts: origin-side, middle section, destination-side.

**Step 2: Keep recommendation quality constraints**

Retain current filtering and anti-hallucination constraints.

### Task 4: Verify Syntax And Import

**Files:**
- Verify: `services/amap.py`
- Verify: `services/llm.py`
- Verify: `main.py`

**Step 1: Compile Python files**

Run: `uv run python -m py_compile main.py database.py models\query.py services\amap.py services\llm.py run.py`
Expected: no output

**Step 2: Verify app import**

Run: `uv run python -c "import main; print('app import ok')"`
Expected: `app import ok`
