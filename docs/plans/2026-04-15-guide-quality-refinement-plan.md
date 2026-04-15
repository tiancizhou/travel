# Guide Quality Refinement Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Improve generated route guides so they stay within supported transport modes, reject long walks more clearly, and recommend only higher-value stops.

**Architecture:** Keep the current generation pipeline, but strengthen two control points: backend POI filtering and mode-aware prompt constraints. Add simple deterministic heuristics for long walking routes before content generation.

**Tech Stack:** FastAPI, Pydantic, httpx, static HTML/CSS/JS, AMap Web Service API, LLM prompt generation

---

### Task 1: Tighten POI Filtering

**Files:**
- Modify: `services/amap.py`

**Step 1: Expand blocked POI keywords**

Add filters for low-value places such as hotels, chain fast food, bars, entertainment-first venues, and generic commercial locations.

**Step 2: Reduce recommendation counts**

Return fewer POIs when quality is weak instead of padding the list.

**Step 3: Keep scenic and food priorities**

Preserve preference for scenic and cultural points, then allow only a very small number of food points.

### Task 2: Add Long-Walk Heuristics

**Files:**
- Modify: `services/llm.py`

**Step 1: Add a walking suitability heuristic**

Use route distance and duration to decide whether walking is suitable for relaxed travel.

**Step 2: Pass the heuristic into prompt construction**

Ensure the prompt gets an explicit instruction when walking is too long.

### Task 3: Tighten Prompt Constraints

**Files:**
- Modify: `services/llm.py`

**Step 1: Disallow unsupported transport modes**

Explicitly forbid recommending riding or driving.

**Step 2: Forbid low-confidence transport claims**

Prevent fabricated line numbers, exit details, or unsupported station details.

**Step 3: Discourage weak stops**

Tell the model not to recommend hotels, generic commercial stops, or low-value fast-food stops as highlights.

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
