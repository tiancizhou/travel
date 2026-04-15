# Guide Quality Refinement Design

## Goal

Improve route guide quality so outputs become more trustworthy, more actionable, and aligned with the current product scope of walking and transit only.

## Problems Observed

- The guide still mentions unsupported modes such as riding.
- POI quality is unstable and often includes low-value commercial or utility locations.
- Long walking routes are not rejected strongly enough.
- The guide still drifts into generic language instead of practical route advice.

## Chosen Approach

Refine guide quality at two layers:

1. Tighten backend POI filtering and route heuristics.
2. Tighten LLM prompt constraints so unsupported transport modes and low-confidence claims are disallowed.

## Rules

### Transport Scope

The guide may only reference:

- walking
- transit

It must never recommend riding or driving.

### Long Walking Rule

If walking distance or duration is beyond a relaxed threshold, the guide must clearly recommend transit instead of framing the route as an easy walk.

Initial heuristic:

- distance greater than 7000 meters, or
- duration greater than 90 minutes

### POI Filtering

Block low-value POIs such as:

- hotels
- chain fast food
- generic office or residential places
- bars and entertainment-first venues
- generic service locations

Prefer:

- scenic points
- cultural and historical places
- parks
- museums
- representative local food

If not enough strong POIs remain, return fewer recommendations rather than padding with weak ones.

## Prompt Refinement

The prompt should explicitly state:

- only walking and transit are valid suggestions
- unsupported modes must not be mentioned
- if walking is too long, recommend switching to transit
- avoid vague hype language
- avoid recommending low-value commercial stops as highlights

## Expected Outcome

- More consistent route advice
- Better alignment with product capabilities
- Fewer embarrassing or low-value recommendations
- More decisive handling of long walking routes
