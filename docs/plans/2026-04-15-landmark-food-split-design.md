# Landmark And Food Split Design

## Goal

Improve route analysis by separating scenic landmarks from food stops, and strengthen destination-side enrichment for large scenic areas.

## Problem

Current output still mixes food stops into main highlights, and large scenic destinations are treated as a single coarse place instead of being broken into core nearby landmarks.

## Chosen Approach

Split enrichment data into two categories before content generation:

- landmarks
- food stops

In addition, detect large scenic destinations and run an extra scenic search around the destination so major internal or adjacent landmarks are more likely to be included.

## Design

### Landmark And Food Separation

- Landmark POIs are used only for route highlights and along-route analysis
- Food POIs are used only for food and replenishment suggestions

### Scenic Destination Enrichment

If the destination name looks like a scenic area or large attraction cluster, run an extra nearby scenic search around the destination coordinates and merge results.

### Prompt Constraints

- Main highlights must only come from landmark candidates
- Food suggestions must only come from food candidates
- The model should analyze origin, mid-route, and destination-side landmarks with stronger emphasis on recognizable places

## Expected Outcome

- Fewer weak commercial places in main highlights
- Better destination-side detail for large attractions
- Cleaner separation between sightseeing and replenishment advice
