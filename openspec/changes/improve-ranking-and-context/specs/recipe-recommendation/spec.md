# Recipe Recommendation Capability - Improvements

## MODIFIED Requirements

### Requirement: Result Ranking
The system SHALL rank search results using a weighted combination of similarity and Bayesian average rating that accounts for both rating quality and review count.

#### Scenario: Apply Bayesian average for ratings
- **WHEN** calculating result order
- **THEN** system computes Bayesian rating as: (C × global_avg + rating × rating_count) / (C + rating_count), where C is confidence threshold

#### Scenario: Calculate global average rating
- **WHEN** processing search results
- **THEN** system calculates weighted global average as: sum(rating × rating_count) / sum(rating_count) across all results

#### Scenario: Use confidence threshold for reliability
- **WHEN** determining rating reliability
- **THEN** system uses 10th percentile of rating counts as confidence threshold to penalize recipes with few reviews

#### Scenario: Apply improved ranking formula
- **WHEN** calculating final rank score
- **THEN** system computes score as: (similarity × 0.6) + (normalized_bayesian_rating × 0.4)

#### Scenario: Normalize Bayesian rating
- **WHEN** incorporating Bayesian rating into rank score
- **THEN** system divides Bayesian rating by 5.0 to normalize to 0-1 scale

#### Scenario: Penalize recipes with few reviews
- **WHEN** recipe has fewer reviews than confidence threshold
- **THEN** system pulls its Bayesian rating toward global average, reducing its rank

#### Scenario: Trust recipes with many reviews
- **WHEN** recipe has significantly more reviews than confidence threshold
- **THEN** system's Bayesian rating approaches the actual recipe rating

#### Scenario: Handle recipes with no reviews
- **WHEN** recipe has zero reviews (rating_count = 0)
- **THEN** system assigns global average rating as its Bayesian rating

#### Scenario: Limit result count
- **WHEN** returning recommendations
- **THEN** system returns top 2 ranked results by default

#### Scenario: Extract result count from query
- **WHEN** user specifies number in query (e.g., "5 recipes", "10 results")
- **THEN** system extracts and uses that number instead of the default

#### Scenario: Prevent duplicate results
- **WHEN** recipes have multiple version entries in database
- **THEN** system uses DISTINCT ON to return each recipe only once

## ADDED Requirements

### Requirement: Conversation Context Tracking
The system SHALL maintain conversation context by tracking query history and extracted filters across multiple turns to enable intelligent query refinement.

#### Scenario: Track filter history
- **WHEN** user submits a query
- **THEN** system stores the extracted filters in session history alongside query text and results

#### Scenario: Retrieve previous filters
- **WHEN** processing a new query
- **THEN** system can access filters from the most recent previous query

#### Scenario: Maintain filter history size
- **WHEN** storing filter history
- **THEN** system maintains a deque with maximum size matching session memory settings (default 5-10)

#### Scenario: Clear filter history on session restart
- **WHEN** chatbot session restarts
- **THEN** system clears all previous filter history

### Requirement: Query Refinement Detection
The system SHALL detect when a user query is a refinement of a previous query and preserve relevant context.

#### Scenario: Detect refinement keywords
- **WHEN** query contains refinement keywords like "under", "with", "without", "also", "but"
- **THEN** system identifies query as refinement and retrieves previous context

#### Scenario: Detect additive patterns
- **WHEN** query contains additive patterns like "I want chicken", "show me vegetarian", "give me pasta"
- **THEN** system identifies query as refinement if query is 6 words or fewer

#### Scenario: Detect protein additions
- **WHEN** query mentions specific protein (chicken, beef, pork, fish, lamb, turkey, seafood)
- **THEN** system treats as refinement and merges with previous filters

#### Scenario: Detect dietary additions
- **WHEN** query mentions dietary restrictions (vegetarian, vegan, gluten) in short query
- **THEN** system treats as refinement and merges with previous filters

#### Scenario: Skip context for complete queries
- **WHEN** query is longer than 8 words and doesn't contain refinement keywords
- **THEN** system treats as new independent query without previous context

#### Scenario: Return context and filters tuple
- **WHEN** detecting refinement
- **THEN** system returns tuple of (previous_query_string, previous_filters_dict)

#### Scenario: Return none for new queries
- **WHEN** query is not a refinement
- **THEN** system returns (None, None) to indicate no previous context

### Requirement: Intelligent Filter Merging
The system SHALL intelligently merge previous query filters with current query filters when processing refinement queries.

#### Scenario: Merge list filters as union
- **WHEN** both previous and current filters contain list fields (tags, dietary_tags, cuisine)
- **THEN** system merges them as union without duplicates

#### Scenario: Override scalar filters
- **WHEN** current filter contains scalar values (max_time, difficulty, result_limit)
- **THEN** system replaces previous value with current value

#### Scenario: Replace protein filter
- **WHEN** current filter specifies new main_protein
- **THEN** system replaces previous main_protein and updates exclude_tags accordingly

#### Scenario: Preserve previous tags when adding protein
- **WHEN** user refines "highly rated recipes" with "I want chicken ones"
- **THEN** system merges to create filters with both rating constraints and chicken protein filter

#### Scenario: Combine dietary and cuisine filters
- **WHEN** user refines "vegetarian recipes" with "make it thai"
- **THEN** system preserves dietary_tags=["vegetarian"] and adds cuisine=["thai"]

#### Scenario: Update exclude_tags with new protein
- **WHEN** current filter specifies main_protein and exclude_tags
- **THEN** system uses current exclude_tags to replace previous ones

#### Scenario: Maintain tag hierarchy
- **WHEN** merging tags from "easy dinner" with "make it vegetarian"
- **THEN** system preserves both difficulty, meal tags, and dietary tags

### Requirement: Context-Aware Recommendations
The system SHALL use conversation context to provide coherent multi-turn recipe discovery experiences.

#### Scenario: Accept previous filters parameter
- **WHEN** recommend() method is called
- **THEN** system accepts optional previous_filters dictionary parameter

#### Scenario: Merge filters before search
- **WHEN** previous_filters are provided
- **THEN** system merges them with newly extracted filters before executing search

#### Scenario: Return merged filters
- **WHEN** returning recommendation results
- **THEN** system returns tuple of (results_list, merged_filters_dict) for future refinements

#### Scenario: Display refinement feedback
- **WHEN** processing refinement query
- **THEN** system displays "I'll refine your previous search..." with previous and new constraints

#### Scenario: Example: Rating then protein refinement
- **WHEN** user asks "Give me some recipes with good rating" then "I want chicken ones"
- **THEN** system returns highly-rated chicken recipes with merged filters

#### Scenario: Example: Dietary then cuisine refinement
- **WHEN** user asks "vegetarian recipes" then "make them italian"
- **THEN** system returns vegetarian Italian recipes preserving both constraints

#### Scenario: Example: Category then time refinement
- **WHEN** user asks "dessert recipes" then "under 30 minutes"
- **THEN** system returns quick desserts preserving category filter

#### Scenario: Store merged filters in session
- **WHEN** refinement query completes
- **THEN** system stores merged filters for potential next refinement
