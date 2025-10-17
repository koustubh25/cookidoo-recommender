# Recipe Recommendation System Design

## Context
The system needs to enable users to discover Thermomix recipes through natural language queries. The Cookidoo recipe database is stored in Google Cloud AlloyDB with pre-computed vector embeddings (768-dimensional) for semantic search. Users want to interact through a chatbot interface and receive recommendations that are compatible with their Thermomix TM6 device.

### Constraints
- Database: Google Cloud AlloyDB with existing schema and vector embeddings
- AI Platform: Google Vertex AI (Gemini models)
- Device: Results must be compatible with Thermomix TM6
- Network: User is on VPN, potential connection issues
- Python interpreter: `/Users/gaikwadk/miniforge3/bin/python3`
- Authentication: Service account JSON file with necessary GCP permissions

## Goals / Non-Goals

### Goals
- Enable natural language recipe queries with high relevance
- Combine semantic search (embeddings) with structured filtering (SQL)
- Ensure TM6 compatibility for all recommendations
- Provide conversational chatbot interface for iterative refinement
- Handle common query patterns (dietary restrictions, time constraints, ingredients, meal types)
- Validate results with sanity tests (e.g., "5 drink recipes" returns only drinks)

### Non-Goals
- Real-time embedding generation (use existing embeddings)
- Recipe scraping or data ingestion (data already exists)
- Multi-user authentication or session management (personal project)
- Production-grade deployment infrastructure
- Support for non-TM6 Thermomix versions (unless explicitly requested)

## Decisions

### Decision 1: Hybrid Search Approach
**What**: Combine NL2SQL for structured filtering with vector similarity search for semantic matching

**Why**:
- NL2SQL allows efficient filtering by dietary tags, cooking time, difficulty, ingredients
- Vector embeddings capture semantic similarity for intent-based matching
- Hybrid approach leverages both structured data and semantic understanding
- Reduces search space before expensive vector operations

**Alternatives Considered**:
- Pure vector search: Would miss structured constraints (e.g., "vegetarian under 30 minutes")
- Pure SQL: Would miss semantic similarity and synonym matching
- LLM-only ranking: Too slow and expensive for personal use

### Decision 2: Two-Stage Query Processing
**What**:
1. Stage 1: Use Gemini to extract structured filters and generate SQL WHERE clause
2. Stage 2: Perform vector similarity search on filtered results

**Why**:
- Reduces vector search space by pre-filtering with SQL
- Gemini can understand natural language constraints and map to database schema
- Vector search on smaller dataset is faster and more relevant
- Allows graceful degradation if one stage fails

**Implementation**:
```python
# Stage 1: NL2SQL
query = "vegetarian recipes under 30 minutes"
filters = gemini.extract_filters(query)  # Returns: {dietary_tags: ["vegetarian"], max_time: 30}
sql_clause = build_where_clause(filters)

# Stage 2: Vector search on filtered set
embedding = gemini.embed(query)
results = db.vector_search(embedding, where=sql_clause, limit=10)
```

### Decision 3: Python Module Structure
**What**: Organize code into focused modules:
- `db/` - Database connection and query operations
- `ai/` - Gemini integration (embeddings, query understanding, chat)
- `recommendations/` - Core recommendation engine and ranking logic
- `chatbot/` - Conversational interface
- `config/` - Configuration and credentials management
- `tests/` - Validation and sanity tests

**Why**:
- Clear separation of concerns
- Easier to test individual components
- Follows Python conventions
- Allows independent evolution of each module

### Decision 4: TM6 Compatibility Filtering
**What**: Always filter `recipe_thermomix_versions` table to ensure TM6 compatibility

**Why**:
- User has TM6 device, incompatible recipes are useless
- Prevents user frustration
- Simple JOIN on versions table

**Implementation**:
```sql
JOIN recipe_thermomix_versions rtv ON r.recipe_id = rtv.recipe_id
WHERE rtv.version = 'TM6'
```

### Decision 5: Gemini Model Selection
**What**: Use `gemini-1.5-flash` for query understanding and `text-embedding-005` for embeddings

**Why**:
- gemini-1.5-flash: Fast, cost-effective for structured extraction tasks
- text-embedding-005: Matches the model used for existing 768-dimensional embeddings in the database
- Both available through Vertex AI in Google Cloud
- Ensures consistency between query embeddings and stored recipe embeddings for accurate similarity search

### Decision 6: Result Ranking Strategy
**What**: Rank results by weighted combination of:
- Vector similarity score (60%)
- User ratings (30%)
- Rating count (10%)

**Why**:
- Vector similarity is primary relevance signal
- Ratings provide quality signal
- Rating count reduces noise from single-review recipes
- Weights can be tuned based on user feedback

**Default Result Limit**: System returns 2 results by default unless explicitly specified in the query (e.g., "5 recipes", "10 results"). This prevents information overload and encourages focused recommendations.

## Risks / Trade-offs

### Risk 1: VPN Connection Issues
- **Risk**: User is on VPN, may have Google Cloud connectivity issues
- **Mitigation**:
  - Add retry logic with exponential backoff
  - Implement connection validation before queries
  - Provide clear error messages for network issues
  - Add timeout configuration

### Risk 2: Gemini API Rate Limits
- **Risk**: Personal project may hit rate limits with frequent queries
- **Mitigation**:
  - Cache Gemini responses for identical queries
  - Batch operations where possible
  - Monitor usage and implement throttling if needed

### Risk 3: Query Understanding Accuracy
- **Risk**: Gemini may misinterpret user queries or extract wrong filters
- **Mitigation**:
  - Show extracted filters to user for confirmation
  - Allow manual filter editing in chatbot
  - Implement fallback to pure vector search if NL2SQL fails
  - Build test suite with diverse query patterns

### Risk 4: Embedding Dimension Mismatch
- **Risk**: Assumed 768 dimensions but actual embeddings may differ
- **Mitigation**:
  - Query database to verify embedding dimensions on startup
  - Document actual embedding model used for existing data
  - Add dimension validation in vector search

### Trade-off: Simplicity vs Performance
- **Trade-off**: Single-stage vs multi-stage processing
- **Decision**: Multi-stage (NL2SQL then vector) despite added complexity
- **Justification**: Performance benefit of pre-filtering outweighs complexity for large recipe database

## Migration Plan

### Phase 1: Core Infrastructure (No existing data migration needed)
1. Set up Python environment and dependencies
2. Implement database connection module
3. Implement Gemini client module
4. Validate connectivity and credentials

### Phase 2: Search Engine
1. Implement NL2SQL query understanding
2. Implement vector similarity search
3. Integrate hybrid search pipeline
4. Add TM6 filtering

### Phase 3: Chatbot Interface
1. Build conversational state management
2. Implement query refinement
3. Add result formatting and presentation

### Phase 4: Testing & Validation
1. Create sanity test suite
2. Test edge cases (ambiguous queries, no results, etc.)
3. Validate TM6 filtering accuracy

### Rollback
Not applicable - new feature with no existing functionality to preserve.

### Decision 7: Ambiguous Query Handling
**What**: When queries are ambiguous or lack specificity, prompt user with clarifying questions

**Why**:
- Ensures accurate intent understanding before executing search
- Reduces irrelevant results from misinterpreted queries
- Improves user experience through interactive refinement
- Prevents wasted API calls on unclear queries

**Implementation Strategy**:
1. Detect ambiguity signals (vague terms like "something good", missing constraints)
2. Ask specific follow-up questions (e.g., "What type of meal? breakfast/lunch/dinner?")
3. Provide example queries to guide users
4. Allow users to proceed with broad search if they prefer

**Examples**:
- Query: "something tasty" → Ask: "What type of dish are you looking for? (appetizer, main course, dessert, drink)"
- Query: "quick recipe" → Ask: "How much time do you have? (under 15 min, 15-30 min, 30-60 min)"
- Query: "healthy meal" → Ask: "Any dietary preferences? (vegetarian, vegan, low-carb, gluten-free)"

### Decision 8: Result Presentation
**What**: Display recipe name and thumbnail as clickable elements that open the Cookidoo URL

**Why**:
- Minimal, clean interface showing essential information
- Thumbnails provide visual appeal and quick recipe identification
- Direct link to Cookidoo allows users to view full recipe details
- Reduces information overload in chatbot interface

**Implementation**:
- Default display: Recipe name + thumbnail image
- Both name and thumbnail are clickable links to recipe URL
- Additional details (rating, cooking time, difficulty) available on hover or as supplementary text
- URL format follows Cookidoo structure for direct navigation

### Decision 9: Conversation Session Memory
**What**: Maintain session history of previous queries and results

**Why**:
- Enables query refinement commands like "show me more like this"
- Allows users to reference previous results
- Improves conversational flow
- Supports iterative recipe discovery

**Implementation**:
- Store last 5-10 queries and their results in session
- Clear session on chatbot restart
- Allow commands like "similar to #2", "show me more drinks"

### Decision 10: Performance Targets
**What**: Target < 10 seconds response time with future optimization goal

**Why**:
- 10 seconds is acceptable for initial implementation
- Provides buffer for network latency (VPN connection)
- Allows for hybrid search without aggressive optimization
- Plan for future performance improvements as usage patterns emerge

**Optimization Strategy**:
- Phase 1: Get it working reliably (< 10s)
- Phase 2: Optimize hot paths (target < 5s)
- Phase 3: Advanced caching and indexing (target < 2s)

### Decision 11: Recipe Name Search
**What**: Include recipe names in searchable text for both SQL filtering and vector search

**Why**:
- Users often search by partial recipe names they remember
- Recipe titles contain important keywords (cuisine, dish type, ingredients)
- Improves recall when users have specific recipes in mind
- Already included in existing embedding text (Title field)

**Implementation**:
- SQL: Add ILIKE pattern matching on recipe title field for name-based filtering
- Vector: Recipe names already embedded in existing vectors (confirmed in embedding generation code)
- Support queries like "chicken curry" to find recipes with those words in title

### Decision 12: IAM Authentication for AlloyDB
**What**: Use Google Cloud IAM authentication instead of username/password for AlloyDB connections

**Why**:
- Enhanced security: No passwords stored in environment variables or code
- Centralized access management: Leverage Google Cloud IAM for authentication and authorization
- Automatic credential rotation: IAM tokens are refreshed automatically
- Better audit trail: All database access logged through Cloud Audit Logs
- Simplified credential management: Single service account for both AlloyDB and Vertex AI access

**Implementation**:
- Load service account credentials from `GCP_SERVICE_ACCOUNT_JSON` file
- Use Cloud SQL Python Connector with `enable_iam_auth=True`
- Service account email as database user (e.g., `my-sa@project.iam.gserviceaccount.com`)
- Grant `roles/alloydb.client` IAM role to service account
- Create IAM-based database user in AlloyDB
- Grant necessary database privileges in PostgreSQL

**Alternatives Considered**:
- Username/password authentication: Rejected due to security concerns and credential management overhead
- Cloud SQL Auth Proxy: Not needed as Cloud SQL Python Connector handles IAM auth directly

**Security Benefits**:
- No static passwords to manage or rotate
- IAM policies control who can access the database
- Service account keys can be rotated without code changes
- Integration with Google Cloud security best practices
