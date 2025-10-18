# Implementation Tasks

## 1. Ranking Algorithm Improvements
- [x] 1.1 Replace normalized rating formula with Bayesian average in `recommendations/engine.py:_rank_results()`
- [x] 1.2 Calculate global average rating weighted by review counts
- [x] 1.3 Implement confidence threshold using 10th percentile of rating counts
- [x] 1.4 Add bayesian_rating field to result dictionaries for debugging

## 2. Context-Aware Session Management
- [x] 2.1 Add filter_history deque to ChatSession class in `chatbot/session.py`
- [x] 2.2 Update add_query() method to accept and store filters parameter
- [x] 2.3 Add get_last_filters() method to retrieve previous query filters
- [x] 2.4 Enhance get_context_for_query() to return tuple of (query, filters)
- [x] 2.5 Add detection patterns for additive refinements (protein types, dietary restrictions)

## 3. Filter Merging Logic
- [x] 3.1 Add previous_filters parameter to recommend() method signature
- [x] 3.2 Implement _merge_filters() method in RecommendationEngine
- [x] 3.3 Handle list field merging (tags, dietary_tags, cuisine) as union
- [x] 3.4 Handle protein replacement with automatic exclude_tags update
- [x] 3.5 Return merged filters along with results for future refinements

## 4. Chatbot Integration
- [x] 4.1 Update _process_query() to extract context and previous_filters
- [x] 4.2 Pass previous_filters to engine.recommend() when refining queries
- [x] 4.3 Store merged filters in session for next iteration
- [x] 4.4 Update user feedback messages to show refinement detection

## 5. Testing and Validation
- [x] 5.1 Verify Python syntax compilation for all modified files
- [x] 5.2 Test ranking with recipes of varying rating counts
- [x] 5.3 Test context detection with refinement queries
- [x] 5.4 Verify filter merging logic preserves previous constraints
