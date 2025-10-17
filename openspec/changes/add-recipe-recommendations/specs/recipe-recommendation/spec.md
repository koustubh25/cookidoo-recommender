# Recipe Recommendation Capability

## ADDED Requirements

### Requirement: Query Understanding
The system SHALL extract structured filters from natural language queries using Gemini AI to enable hybrid search.

#### Scenario: Extract dietary restrictions
- **WHEN** user queries "vegetarian recipes"
- **THEN** system extracts dietary_tags filter containing "vegetarian"

#### Scenario: Extract time constraints
- **WHEN** user queries "quick meals under 30 minutes"
- **THEN** system extracts max_time filter with value 30

#### Scenario: Extract multiple filters
- **WHEN** user queries "easy vegetarian dinner under 45 minutes"
- **THEN** system extracts dietary_tags=["vegetarian"], tags=["dinner"], max_time=45, difficulty=["easy"]

#### Scenario: Detect ambiguous queries
- **WHEN** user queries "something good"
- **THEN** system detects ambiguity and asks clarifying questions before executing search

#### Scenario: Ask clarifying questions for meal type
- **WHEN** user query lacks meal type specification
- **THEN** system prompts "What type of dish are you looking for? (appetizer, main course, dessert, drink)"

#### Scenario: Ask clarifying questions for time constraints
- **WHEN** user queries "quick recipe" without specific time
- **THEN** system asks "How much time do you have? (under 15 min, 15-30 min, 30-60 min)"

#### Scenario: Allow user to proceed with broad search
- **WHEN** user declines to provide clarifications
- **THEN** system performs vector search without structured filters using the original query

#### Scenario: Search by recipe name
- **WHEN** user queries with recipe name keywords like "chicken curry"
- **THEN** system applies SQL ILIKE pattern matching on title field and includes in vector search

#### Scenario: Partial recipe name matching
- **WHEN** user provides partial recipe name
- **THEN** system returns recipes with titles containing the provided keywords

#### Scenario: Extract nutritional requirements
- **WHEN** user queries "high protein vegetarian recipes"
- **THEN** system extracts high_protein=true and dietary_tags=["vegetarian"]

#### Scenario: Filter desserts from nutritional queries
- **WHEN** user queries "high protein recipes" or "low fat meals"
- **THEN** system excludes dessert/cake tags to focus on savory dishes

#### Scenario: Apply nutritional filters per serving
- **WHEN** high_protein filter is true
- **THEN** system filters for recipes with >20g protein per serving (calculated as total_protein / servings)

#### Scenario: Apply low fat filter per serving
- **WHEN** low_fat filter is true
- **THEN** system filters for recipes with <10g fat per serving (calculated as total_fat / servings)

#### Scenario: Apply low carb filter per serving
- **WHEN** low_carb filter is true
- **THEN** system filters for recipes with <30g carbs per serving (calculated as total_carbs / servings)

#### Scenario: Apply low calorie filter per serving
- **WHEN** low_calorie filter is true
- **THEN** system filters for recipes with <300 kcal per serving (calculated as total_calories / servings)

#### Scenario: Display per-serving nutrition
- **WHEN** returning recipe results
- **THEN** system displays nutrition values calculated per serving in format: "Nutrition (per serving, X servings): Y kcal, Zg protein, Ag carbs, Bg fat"

### Requirement: Hybrid Search
The system SHALL combine NL2SQL filtering with vector similarity search to retrieve relevant recipes.

#### Scenario: Two-stage search execution
- **WHEN** user submits a query with extractable filters
- **THEN** system first applies SQL WHERE clause to filter recipes, then performs vector similarity search on filtered results

#### Scenario: Fallback to vector-only search
- **WHEN** NL2SQL filter extraction fails
- **THEN** system performs pure vector similarity search on full dataset

#### Scenario: Vector similarity ranking
- **WHEN** multiple recipes match the filters
- **THEN** system ranks results by cosine similarity to query embedding

### Requirement: TM6 Compatibility
The system SHALL only return recipes compatible with Thermomix TM6 device.

#### Scenario: Filter by device version
- **WHEN** searching for recipes
- **THEN** system joins with recipe_thermomix_versions table and filters where version='TM6'

#### Scenario: No TM6 compatible results
- **WHEN** query yields no TM6-compatible recipes
- **THEN** system returns empty result set with message indicating no compatible recipes found

### Requirement: Result Ranking
The system SHALL rank search results using a weighted combination of similarity, ratings, and popularity.

#### Scenario: Apply ranking formula
- **WHEN** calculating result order
- **THEN** system computes score as: (similarity * 0.6) + (normalized_rating * 0.3) + (normalized_rating_count * 0.1)

#### Scenario: Limit result count
- **WHEN** returning recommendations
- **THEN** system returns top 2 ranked results by default

#### Scenario: Extract result count from query
- **WHEN** user specifies number in query (e.g., "5 recipes", "10 results")
- **THEN** system extracts and uses that number instead of the default

#### Scenario: Prevent duplicate results
- **WHEN** recipes have multiple version entries in database
- **THEN** system uses DISTINCT ON to return each recipe only once

### Requirement: Database Connectivity
The system SHALL connect to Google Cloud AlloyDB using IAM authentication with service account credentials.

#### Scenario: Establish IAM authenticated connection
- **WHEN** system initializes
- **THEN** system loads service account JSON file and establishes AlloyDB connection using IAM authentication

#### Scenario: Use IAM authentication
- **WHEN** connecting to AlloyDB
- **THEN** system uses service account email as database user with enable_iam_auth=True

#### Scenario: Handle connection failures
- **WHEN** connection to AlloyDB fails
- **THEN** system retries with exponential backoff up to 3 attempts and reports clear error message

#### Scenario: Validate connection on startup
- **WHEN** system starts
- **THEN** system verifies database connectivity and embedding dimension compatibility

#### Scenario: No password authentication
- **WHEN** authenticating to AlloyDB
- **THEN** system uses only IAM tokens and does not require or store database passwords

### Requirement: Gemini Integration
The system SHALL use Google Vertex AI Gemini models for query understanding and embeddings.

#### Scenario: Generate query embeddings
- **WHEN** user submits a query
- **THEN** system generates 768-dimensional embedding using text-embedding-005 model

#### Scenario: Extract filters with Gemini
- **WHEN** processing natural language query
- **THEN** system calls gemini-1.5-flash to extract structured filters in JSON format

#### Scenario: Handle Gemini API errors
- **WHEN** Gemini API call fails
- **THEN** system logs error and falls back to vector-only search

### Requirement: Query Ambiguity Detection
The system SHALL detect ambiguous or vague queries and request clarification from the user.

#### Scenario: Provide example queries for guidance
- **WHEN** user submits ambiguous query
- **THEN** system shows example queries like "vegetarian pasta under 30 minutes" or "easy desserts for beginners"

#### Scenario: Detect vague descriptors
- **WHEN** query contains only vague terms like "tasty", "good", "nice"
- **THEN** system asks for specific attributes (meal type, cuisine, dietary needs, time available)

#### Scenario: Progressive clarification
- **WHEN** user provides partial clarification
- **THEN** system asks follow-up questions until sufficient specificity is achieved or user opts to proceed

### Requirement: Chatbot Interface
The system SHALL provide a conversational interface for recipe discovery.

#### Scenario: Accept natural language input
- **WHEN** user types a recipe query
- **THEN** system processes query and returns formatted recommendations

#### Scenario: Display recipe results
- **WHEN** recommendations are returned
- **THEN** system displays recipe name and thumbnail image as clickable links to Cookidoo URL for each recipe

#### Scenario: Recipe links open Cookidoo page
- **WHEN** user clicks on recipe name or thumbnail
- **THEN** system opens the recipe URL in browser to view full details on Cookidoo

#### Scenario: Support query refinement
- **WHEN** user requests "show me more like this"
- **THEN** system uses previous result as seed for similarity search

#### Scenario: Maintain session memory
- **WHEN** user interacts with chatbot during a session
- **THEN** system stores last 5-10 queries and their results for reference

#### Scenario: Reference previous results
- **WHEN** user commands "similar to #2" or "show me more drinks"
- **THEN** system retrieves the referenced query from session history and performs related search

#### Scenario: Clear session on restart
- **WHEN** chatbot restarts
- **THEN** system clears previous session memory and starts fresh

#### Scenario: Handle no results
- **WHEN** query returns zero results
- **THEN** system suggests broadening search criteria or removing filters

### Requirement: Result Validation
The system SHALL validate recommendation accuracy through sanity tests.

#### Scenario: Validate category matching
- **WHEN** testing with query "5 drink recipes"
- **THEN** system returns 5 results where all have tag "drinks" or "beverages"

#### Scenario: Validate time constraints
- **WHEN** testing with query "recipes under 20 minutes"
- **THEN** system returns results where total_time_minutes <= 20

#### Scenario: Validate dietary restrictions
- **WHEN** testing with query "vegan meals"
- **THEN** system returns results where all have dietary_tag "vegan"

### Requirement: Error Handling
The system SHALL handle errors gracefully and provide actionable feedback.

#### Scenario: Network connectivity issues
- **WHEN** VPN causes connection timeout
- **THEN** system retries request and displays "Connection issues detected, retrying..." message

#### Scenario: Invalid query input
- **WHEN** user submits empty or nonsensical query
- **THEN** system prompts user with example queries

#### Scenario: Embedding dimension mismatch
- **WHEN** query embedding dimensions don't match database
- **THEN** system raises validation error with details on expected vs actual dimensions

### Requirement: Configuration Management
The system SHALL support configurable parameters for search and ranking.

#### Scenario: Configure result limit
- **WHEN** user wants more than 2 results
- **THEN** system extracts limit from query or accepts configurable limit parameter (max 50)

#### Scenario: Configure ranking weights
- **WHEN** system is initialized
- **THEN** system loads ranking weights from config file or uses defaults

#### Scenario: Configure retry behavior
- **WHEN** connection issues occur
- **THEN** system uses configurable retry count and backoff settings
