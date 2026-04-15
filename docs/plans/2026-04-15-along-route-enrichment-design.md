# Along-Route Enrichment Design

## Goal

Improve route analysis so guides can reference meaningful places across the whole route, not just the origin and destination.

## Problem

Current route analysis misses important mid-route landmarks. For example, a route crossing central Nanjing may pass near city-wall, museum, and scenic areas, but the guide may only mention endpoint-adjacent POIs.

## Chosen Approach

Increase along-route coverage by sampling more points across the route and searching a broader set of scenic and cultural POIs around each sample point.

## Design

### Route Sampling

- Increase route sample count from a very small set to a denser set
- Spread samples across the entire route rather than favoring only endpoints

### Search Coverage

- Increase search radius per sample point
- Focus on scenic, cultural, museum, park, and historic categories
- Keep a small amount of food only as secondary support data

### Deduplication

- Merge duplicate POIs by name
- Keep near-route ordering where possible

### Prompt Use

- The LLM should be encouraged to interpret the route in three broad parts:
  - origin-side area
  - mid-route area
  - destination-side area

It should not list all POIs mechanically, but it should analyze the line as a route corridor instead of a start-end pair.

## Expected Outcome

- Better recognition of mid-route landmarks
- Richer route suggestions
- More convincing local analysis for long urban routes
