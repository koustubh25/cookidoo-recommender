# Thermomix Recipe Recommendation System

An intelligent recipe recommendation chatbot that helps you discover Thermomix TM6 recipes from your Cookidoo database using natural language queries.

## Features

- **Hybrid Search**: Combines NL2SQL filtering with vector similarity search for accurate results
- **Natural Language Understanding**: Uses Google Gemini AI to understand queries like "easy vegetarian dinner under 30 minutes"
- **TM6 Compatibility**: Automatically filters recipes compatible with Thermomix TM6
- **Conversational Interface**: Interactive chatbot with session memory
- **Intelligent Ranking**: Results ranked by relevance, ratings, and popularity
- **Recipe Name Search**: Find recipes by partial name matching
- **Ambiguity Detection**: Asks clarifying questions for vague queries

## Architecture

```
├── config/          # Configuration and settings
├── db/              # AlloyDB connection and queries
├── ai/              # Gemini AI client for embeddings and NL understanding
├── recommendations/ # Core recommendation engine with hybrid search
├── chatbot/         # Interactive chatbot interface
└── tests/           # Sanity tests and validation
```

## Prerequisites

- Python 3.9+
- Google Cloud Platform account with:
  - AlloyDB instance with recipe database
  - Vertex AI API enabled
  - Service account with these roles:
    - `Cloud AlloyDB Client` (for database access)
    - `Vertex AI User` (for Gemini API access)
    - Database IAM user access granted in AlloyDB
- Thermomix TM6 compatible recipes in database

## Installation

1. **Clone the repository**

```bash
cd ask-recipes
```

2. **Install dependencies**

```bash
/Users/gaikwadk/miniforge3/bin/python3 -m pip install -r requirements.txt
```

3. **Enable AlloyDB Public IP**

In the Google Cloud Console:
- Navigate to your AlloyDB instance
- Enable Public IP address
- Add your machine's IP to the authorized networks
- Note the public IP address

4. **Configure environment variables**

Copy `.env.example` to `.env` and fill in your configuration:

```bash
cp .env.example .env
```

Edit `.env` with your details:

```env
GCP_PROJECT_ID=your-gcp-project-id
GCP_SERVICE_ACCOUNT_JSON=path/to/service-account.json

# AlloyDB public IP connection
ALLOYDB_HOST=34.87.123.45  # Your AlloyDB public IP
ALLOYDB_PORT=5432
ALLOYDB_DATABASE=your-database-name
ALLOYDB_USER=your-database-username
ALLOYDB_PASSWORD=your-database-password
```

**Important**: This system connects to AlloyDB via **public IP** with username/password authentication. Make sure:
- AlloyDB instance has public IP enabled
- Your IP address is in the authorized networks list
- Database user has the necessary privileges

## Usage

### Start the Chatbot

```bash
python run_chatbot.py
```

Or with the full path:

```bash
/Users/gaikwadk/miniforge3/bin/python3 run_chatbot.py
```

### Example Queries

- `easy vegetarian dinner under 30 minutes`
- `quick breakfast recipes`
- `chocolate desserts`
- `chicken curry`
- `vegan pasta dishes`
- `drinks for party`

### Special Commands

- `/history` - View your query history
- `/similar #N` - Find recipes similar to result #N from last query
- `/help` - Show help message
- `/quit` or `/exit` - Exit the chatbot

### Example Session

```
🍳 Thermomix Recipe Recommendation Assistant

You: easy vegetarian pasta under 30 minutes

Bot: Searching for recipes...

Found 10 recipes:

[#1] Quick Vegetarian Pasta Primavera
    URL: https://cookidoo.com/recipes/...
    Image: https://...
    Rating: 4.5/5.0 (120 reviews)
    Time: 25 minutes
    Difficulty: Easy

[#2] Simple Pesto Pasta
    URL: https://cookidoo.com/recipes/...
    Rating: 4.8/5.0 (85 reviews)
    Time: 15 minutes
    Difficulty: Easy

...

You: /similar #1

Bot: Finding recipes similar to 'Quick Vegetarian Pasta Primavera'...
...
```

## Running Tests

Run the sanity test suite:

```bash
/Users/gaikwadk/miniforge3/bin/python3 tests/sanity_tests.py
```

Tests include:
- Drink recipes return only drinks
- Vegetarian queries return vegetarian recipes
- Time constraints are respected
- Recipe name search works correctly
- All results are TM6 compatible

## Configuration

### Settings (config/settings.py)

- `RESULT_LIMIT`: Number of results to return (default: 10)
- `SESSION_MEMORY_SIZE`: Number of queries to remember (default: 10)
- `RESPONSE_TIMEOUT_SECONDS`: Query timeout (default: 10)
- `MAX_RETRIES`: Database connection retries (default: 3)
- `SIMILARITY_WEIGHT`: Weight for vector similarity (default: 0.6)
- `RATING_WEIGHT`: Weight for user ratings (default: 0.3)
- `RATING_COUNT_WEIGHT`: Weight for rating count (default: 0.1)

## How It Works

### Two-Stage Hybrid Search

1. **Stage 1: Filter Extraction (NL2SQL)**
   - Gemini analyzes the query and extracts structured filters
   - Filters include dietary tags, time constraints, difficulty, etc.
   - Falls back to pure vector search if extraction fails

2. **Stage 2: Vector Similarity Search**
   - Generates 768-dimensional embedding of the query using text-embedding-005
   - Performs cosine similarity search against recipe embeddings
   - Applies extracted filters to reduce search space

3. **Result Ranking**
   - Ranks results using weighted formula:
     - Similarity (60%) + Rating (30%) + Rating Count (10%)
   - Ensures TM6 compatibility for all results

### Ambiguity Detection

The system detects vague queries and asks clarifying questions:

- `"something tasty"` → `"What type of dish are you looking for?"`
- `"quick recipe"` → `"How much time do you have?"`

## Troubleshooting

### AlloyDB Public IP Setup

To enable public IP access for AlloyDB:

1. **Enable public IP on your AlloyDB instance:**
   ```bash
   gcloud alloydb instances update YOUR_INSTANCE \
     --cluster=YOUR_CLUSTER \
     --region=YOUR_REGION \
     --assign-inbound-public-ip=PRIMARY
   ```

2. **Add authorized network (your IP address):**
   ```bash
   gcloud alloydb instances update YOUR_INSTANCE \
     --cluster=YOUR_CLUSTER \
     --region=YOUR_REGION \
     --authorized-external-networks=YOUR_IP_ADDRESS/32
   ```

3. **Get the public IP address:**
   ```bash
   gcloud alloydb instances describe YOUR_INSTANCE \
     --cluster=YOUR_CLUSTER \
     --region=YOUR_REGION \
     --format="value(ipAddress)"
   ```

4. **Verify service account has these IAM roles:**
   - `roles/aiplatform.user` - For Vertex AI/Gemini access

### Connection Issues

**"Connection refused" or "Connection timeout" errors:**

1. **Verify AlloyDB public IP is enabled:**
   - Check in Google Cloud Console that your instance has a public IP
   - Get the IP address from instance details

2. **Check firewall/authorized networks:**
   ```bash
   # Find your current IP
   curl ifconfig.me

   # Ensure it's in the authorized networks list
   gcloud alloydb instances describe YOUR_INSTANCE \
     --cluster=YOUR_CLUSTER \
     --region=YOUR_REGION \
     --format="value(authorizedExternalNetworks)"
   ```

3. **Test connectivity:**
   ```bash
   # Test if port is reachable
   nc -zv YOUR_ALLOYDB_IP 5432

   # Or use telnet
   telnet YOUR_ALLOYDB_IP 5432
   ```

4. **Verify credentials:**
   - Check username and password in `.env` file
   - Ensure the database user has necessary privileges
   - Test connection with psql:
     ```bash
     psql "host=YOUR_IP port=5432 dbname=YOUR_DB user=YOUR_USER sslmode=require"
     ```

5. **Check SSL requirements:**
   - AlloyDB public IP connections require SSL
   - The code automatically enables SSL (`ssl_context=True`)
   - If you see SSL errors, check your pg8000 version

### No Results

If queries return no results:
- Try broader search terms
- Remove time constraints
- Check if recipes exist for TM6 in your database

### Embedding Dimension Mismatch

If you see dimension errors:
- Verify that your database embeddings are 768-dimensional
- Check that embeddings were created with text-embedding-005

### API Rate Limits

For personal use, you may hit Gemini API limits:
- The system caches identical queries
- Consider reducing query frequency
- Check your GCP quotas

## Database Schema

The system expects the following AlloyDB schema:

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE recipes (
    id SERIAL PRIMARY KEY,
    recipe_id VARCHAR(255) UNIQUE NOT NULL,
    title TEXT,
    url TEXT,
    total_time_minutes INTEGER,
    difficulty VARCHAR(50),
    rating FLOAT,
    rating_count INTEGER,
    image_url TEXT,
    embedding vector(768)
);

CREATE TABLE recipe_thermomix_versions (
    id SERIAL PRIMARY KEY,
    recipe_id VARCHAR(255) REFERENCES recipes(recipe_id),
    version VARCHAR(50)
);

CREATE TABLE recipe_dietary_tags (
    id SERIAL PRIMARY KEY,
    recipe_id VARCHAR(255) REFERENCES recipes(recipe_id),
    dietary_tag VARCHAR(255)
);

CREATE TABLE recipe_tags (
    id SERIAL PRIMARY KEY,
    recipe_id VARCHAR(255) REFERENCES recipes(recipe_id),
    tag VARCHAR(255)
);
```

## Performance

- Target response time: < 10 seconds
- Actual performance depends on:
  - VPN connection latency
  - Database size
  - Number of filters applied
  - Gemini API response time

## Future Improvements

Phase 2 optimizations (target < 5 seconds):
- Query result caching
- Index optimization
- Connection pooling tuning

Phase 3 optimizations (target < 2 seconds):
- Pre-computed filter combinations
- Materialized views
- Advanced caching strategies

## License

Personal project for Thermomix TM6 recipe discovery.

## Support

For issues or questions, check the logs:
- `chatbot.log` - Chatbot session logs
- Application logs include detailed error messages and stack traces
