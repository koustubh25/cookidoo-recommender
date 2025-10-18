# Improve Ranking Algorithm and Context-Aware Filtering

## Why
The current recommendation system has two critical issues:
1. **Rating sorting doesn't properly account for review count** - A recipe with 5.0 rating and 1 review ranks equally with a 4.8 rating and 100 reviews, leading to unreliable recommendations when users ask for "highly rated recipes"
2. **No conversation context for filters** - When users refine queries (e.g., "Give me some recipes with good rating" followed by "I want chicken ones"), the system doesn't preserve previous filters, resulting in chicken recipes without the rating constraint

These issues reduce recommendation quality and create a poor conversational experience.

## What Changes
- Replace simple normalized rating scoring with **Bayesian average** that weights ratings by review count
- Add **filter history tracking** to ChatSession to maintain previous query filters
- Implement **intelligent filter merging** to combine previous and current filters during query refinement
- Enhance **context detection** to recognize additive refinement patterns (e.g., "I want chicken ones", "show me vegetarian options")
- Update recommendation engine to accept and merge previous filters when processing refinement queries

## Impact
- Affected specs: `recipe-recommendation` (modified capability)
- Affected code:
  - `recommendations/engine.py` - Modified ranking algorithm and filter merging
  - `chatbot/session.py` - Added filter history tracking
  - `chatbot/interface.py` - Updated to use context-aware recommendations
- Dependencies: No new dependencies
- Breaking changes: None (internal algorithm improvements)
