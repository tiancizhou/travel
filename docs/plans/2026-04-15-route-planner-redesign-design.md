# Route Planner Redesign Design

## Goal

Refocus the product from full-route guide generation to a route planner with waypoint support and per-point AI analysis.

## Product Direction

The new experience should do two things clearly:

1. Build a route from start, waypoints, and end.
2. Let the user click any marked point to trigger AI analysis for that location.

The system should no longer treat the whole route as a single long-form guide output.

## Chosen Approach

Use a waypoint-based route planner with a separate point-analysis capability.

## Core Interactions

### Map Clicks

- first click: start
- second click: end
- later clicks: append waypoints

### Point Analysis

- clicking any marker opens point details
- AI analysis runs for that specific point only
- analysis focuses on nearby attractions, why the point matters, and suggested stop time

### Route Generation

- route generation uses only start, waypoints, and end
- output is route geometry plus route summary
- no long-form route guide is required

## Backend Changes

- `/api/plan` should accept waypoints
- add a point-analysis endpoint such as `/api/analyze-point`
- point-analysis uses reverse geocode, nearby POI search, and LLM summary for the selected point

## Frontend Changes

- right panel becomes a control and details area
- show ordered point list with remove controls for waypoints
- show selected-point analysis in the panel or modal
- route result focuses on map line and waypoint sequence

## Expected Outcome

- clearer route-building flow
- AI is applied where it adds value: per-point insights
- less noisy and more controllable than full-route long-form content
