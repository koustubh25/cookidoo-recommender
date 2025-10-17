# Implementation Tasks

## 1. Project Setup
- [x] 1.1 Create project directory structure (db/, ai/, recommendations/, chatbot/, config/, tests/)
- [x] 1.2 Create requirements.txt with dependencies (google-cloud-aiplatform, google-cloud-alloydb-connector, pg8000, google-auth, python-dotenv)
- [x] 1.3 Set up configuration management for credentials and parameters
- [x] 1.4 Create .env.example file documenting required environment variables (IAM auth, no password)

## 2. Database Module
- [x] 2.1 Implement AlloyDB connection manager with IAM authentication using service account
- [x] 2.2 Add connection retry logic with exponential backoff
- [x] 2.3 Implement connection validation and embedding dimension verification
- [x] 2.4 Create query builder for TM6-filtered recipe searches
- [x] 2.5 Implement vector similarity search function using pgvector
- [x] 2.6 Add database error handling and logging
- [x] 2.7 Configure IAM-based authentication (no password required)

## 3. AI Module
- [x] 3.1 Initialize Vertex AI client with service account credentials
- [x] 3.2 Implement query embedding generation using text-embedding-005
- [x] 3.3 Create prompt template for filter extraction with Gemini
- [x] 3.4 Implement filter extraction using gemini-1.5-flash
- [x] 3.5 Add response parsing to convert Gemini output to structured filters
- [x] 3.6 Implement error handling and fallback for AI API failures
- [x] 3.7 Add caching for identical queries to reduce API calls

## 4. Recommendation Engine
- [x] 4.1 Implement hybrid search orchestrator (NL2SQL + vector search)
- [x] 4.2 Create SQL WHERE clause builder from extracted filters
- [x] 4.3 Add recipe name search with SQL ILIKE pattern matching on title field
- [x] 4.4 Implement result ranking with weighted scoring (similarity 60%, rating 30%, count 10%)
- [x] 4.5 Add normalization functions for rating and rating_count
- [x] 4.6 Implement result limiting and pagination logic
- [x] 4.7 Create recipe result formatter (name and thumbnail as clickable links to URL)
- [x] 4.8 Add TM6 compatibility verification in results

## 5. Chatbot Interface
- [x] 5.1 Create command-line chatbot interface with input/output formatting
- [x] 5.2 Implement session memory to store last 5-10 queries and results
- [x] 5.3 Implement conversation state management for query refinement
- [x] 5.4 Add result display with clickable recipe name and thumbnail links
- [x] 5.5 Implement URL opening functionality for recipe links
- [x] 5.6 Add support for referencing previous results (e.g., "similar to #2")
- [x] 5.7 Implement ambiguity detection and clarifying question prompts
- [x] 5.8 Implement "show more" and "refine search" commands
- [x] 5.9 Add example queries and help text
- [x] 5.10 Create interactive mode with continuous conversation loop
- [x] 5.11 Add session clear on chatbot restart
- [x] 5.12 Add graceful exit handling

## 6. Testing and Validation
- [x] 6.1 Create sanity test suite with diverse query patterns
- [x] 6.2 Implement test: "5 drink recipes" returns only drinks
- [x] 6.3 Implement test: "vegetarian meals" returns only vegetarian recipes
- [x] 6.4 Implement test: "recipes under 20 minutes" validates time constraints
- [x] 6.5 Implement test: Recipe name search (e.g., "chicken curry") returns matching titles
- [x] 6.6 Implement test: All results are TM6 compatible
- [x] 6.7 Implement test: Session memory stores and retrieves queries correctly
- [x] 6.8 Implement test: Ambiguous queries trigger clarifying questions
- [x] 6.9 Add edge case tests (empty query, no results, network failure)
- [x] 6.10 Implement test: Response time is under 10 seconds
- [x] 6.11 Create integration test for full query-to-result pipeline

## 7. Documentation and Polish
- [x] 7.1 Add docstrings to all modules and functions
- [x] 7.2 Create README.md with setup instructions and usage examples
- [x] 7.3 Document configuration options and environment variables
- [x] 7.4 Add inline comments for complex logic
- [x] 7.5 Create example queries document for users
- [x] 7.6 Add troubleshooting section for common errors (VPN, credentials, etc.)

## 8. Integration and Deployment
- [x] 8.1 Test end-to-end with real AlloyDB connection
- [x] 8.2 Validate service account permissions for AlloyDB and Vertex AI
- [x] 8.3 Test VPN connectivity and retry behavior
- [x] 8.4 Run full sanity test suite against production data
- [x] 8.5 Performance testing (measure response times)
- [x] 8.6 Create startup script for easy chatbot launch
