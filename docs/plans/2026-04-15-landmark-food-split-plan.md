# Landmark And Food Split Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Separate route landmark analysis from food-stop suggestions, and enrich large scenic destinations with more specific nearby landmarks.

**Architecture:** Adjust AMap enrichment so route-adjacent POIs are categorized into landmarks and food stops before LLM generation. Add a destination-side scenic enrichment pass for large scenic endpoints. Update prompt construction so sightseeing and replenishment recommendations come from different source lists.

**Tech Stack:** FastAPI, Pydantic, httpx, AMap Web Service API, LLM prompt generation

---

### Task 1: Split POIs Into Landmark And Food Lists

**Files:**
- Modify: `services/amap.py`

**Step 1: Refactor POI filtering output**

Return a structured split between landmark candidates and food candidates.

**Step 2: Preserve current blocked-keyword logic**

Keep low-value places filtered out before categorization.

### Task 2: Enrich Scenic Destinations

**Files:**
- Modify: `services/amap.py`
- Modify: `main.py`

**Step 1: Detect scenic-style destinations**

If the destination name suggests a scenic cluster, trigger an extra scenic nearby search around destination coordinates.

**Step 2: Merge and deduplicate extra scenic landmarks**

Prioritize landmark quality without mixing the results into food suggestions.

### Task 3: Update LLM Inputs And Prompt Constraints

**Files:**
- Modify: `services/llm.py`
- Modify: `main.py`

**Step 1: Pass landmarks and food separately**

Provide separate sections in the prompt.

**Step 2: Enforce section-specific usage**

Require the model to use landmarks for highlights and food stops for replenishment only.

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
