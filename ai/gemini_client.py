"""Gemini AI client for embeddings and query understanding."""

import json
import logging
from typing import List, Dict, Any, Optional
from functools import lru_cache
import vertexai
from vertexai.language_models import TextEmbeddingModel
from vertexai.generative_models import GenerativeModel
from config.settings import settings

logger = logging.getLogger(__name__)


class GeminiClient:
    """Client for interacting with Vertex AI Gemini models."""

    def __init__(self):
        """Initialize Vertex AI and models."""
        try:
            vertexai.init(
                project=settings.GCP_PROJECT_ID,
                location=settings.VERTEX_AI_LOCATION
            )
            self.embedding_model = TextEmbeddingModel.from_pretrained(settings.EMBEDDING_MODEL)
            self.gemini_model = GenerativeModel(settings.GEMINI_MODEL)
            logger.info("Gemini client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {str(e)}")
            raise

    @lru_cache(maxsize=128)
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate 768-dimensional embedding for text using text-embedding-005.

        Args:
            text: Input text to embed

        Returns:
            List of 768 floats representing the embedding
        """
        try:
            embeddings = self.embedding_model.get_embeddings([text])
            embedding_vector = embeddings[0].values
            logger.debug(f"Generated embedding with {len(embedding_vector)} dimensions")
            return embedding_vector
        except Exception as e:
            logger.error(f"Embedding generation failed: {str(e)}")
            raise

    def extract_filters(self, query: str) -> Dict[str, Any]:
        """
        Extract structured filters from natural language query using Gemini.

        Args:
            query: Natural language recipe query

        Returns:
            Dictionary of extracted filters
        """
        prompt = self._build_filter_extraction_prompt(query)

        try:
            response = self.gemini_model.generate_content(prompt)
            filters = self._parse_filter_response(response.text)
            logger.info(f"Extracted filters: {filters}")
            return filters
        except Exception as e:
            logger.error(f"Filter extraction failed: {str(e)}")
            # Return empty filters to allow fallback to pure vector search
            return {}

    def _build_filter_extraction_prompt(self, query: str) -> str:
        """Build prompt for filter extraction."""
        return f"""
You are a recipe search assistant. Extract structured filters from the user's query.

User query: "{query}"

Extract the following filters if present:
- dietary_tags: List of dietary restrictions (vegetarian, vegan, gluten-free, nut-free, mediterranean, lactose-free, sugar-free, etc.)
- tags: List of meal types or categories (breakfast, lunch, dinner, snack, appetizer, main dishes, desserts, soups, salads, side dishes, drinks, low-fat, low-carb)
- max_time: Maximum cooking time in minutes (if query mentions "under X minutes" or "quick")
- min_time: Minimum cooking time in minutes
- difficulty: List of difficulty levels (easy, medium, hard)
- recipe_name: Specific recipe name keywords if mentioned
- main_protein: Main protein type if mentioned (chicken, beef, pork, lamb, fish, seafood, turkey, duck)
- exclude_tags: Tags to exclude from results (e.g., if user asks for "chicken", exclude "beef", "pork", "lamb")
- high_protein: true if query mentions high protein or protein-rich (exclude if desserts or cakes mentioned)
- low_fat: true if query mentions low fat or reduced fat (exclude if desserts or cakes mentioned)
- low_carb: true if query mentions low carb or keto
- low_calorie: true if query mentions low calorie or light
- result_limit: number if query specifies how many results (e.g., "5 recipes", "10 results")

IMPORTANT RULES:
1. If the query mentions "dessert", "cake", "sweet", or "pastry", DO NOT set high_protein=true or low_fat=true
2. If the query mentions nutritional requirements (protein, low fat), exclude dessert-related tags
3. When user asks for generic "recipes" WITHOUT explicit category, default to meal categories: ["mains", "soups", "salads"]
4. Only include specific categories (desserts, drinks, side dishes, breakfast) if EXPLICITLY mentioned
5. For vegetarian/vegan queries without explicit category, include mains, soups, and salads
6. When a main protein is mentioned (e.g., "chicken"), set main_protein and exclude_tags for other proteins (e.g., exclude_tags: ["beef", "pork", "lamb", "fish"])
7. main_protein should match recipe title or tags, NOT just ingredients (to avoid matching "chicken stock paste" in beef recipes)

Return your answer as a JSON object. If a filter is not mentioned, omit it from the response.
Only return the JSON, no other text.

Example 1:
Query: "easy vegetarian dinner under 30 minutes"
Response: {{"dietary_tags": ["vegetarian"], "tags": ["dinner", "mains", "soups", "salads"], "max_time": 30, "difficulty": ["easy"]}}

Example 2:
Query: "quick vegetarian recipes, high protein and low fat"
Response: {{"dietary_tags": ["vegetarian"], "tags": ["mains", "soups", "salads"], "max_time": 30, "high_protein": true, "low_fat": true}}

Example 3:
Query: "give me a vegetarian recipe"
Response: {{"dietary_tags": ["vegetarian"], "tags": ["mains", "soups", "salads"]}}

Example 4:
Query: "vegetarian desserts"
Response: {{"dietary_tags": ["vegetarian"], "tags": ["desserts"]}}

Example 5:
Query: "gluten free nut free desserts"
Response: {{"dietary_tags": ["gluten free", "nut free"], "tags": ["desserts"]}}

Example 5a:
Query: "2 recipes"
Response: {{"tags": ["mains", "soups", "salads"], "result_limit": 2}}

Example 6:
Query: "chicken curry"
Response: {{"recipe_name": "chicken curry", "main_protein": "chicken", "exclude_tags": ["beef", "pork", "lamb", "fish"]}}

Example 7:
Query: "chocolate cake"
Response: {{"recipe_name": "chocolate cake", "tags": ["desserts"]}}

Example 8:
Query: "5 easy breakfast recipes"
Response: {{"tags": ["breakfast"], "difficulty": ["easy"], "result_limit": 5}}

Example 9:
Query: "vegan low carb meals"
Response: {{"dietary_tags": ["vegan"], "tags": ["mains", "soups", "salads"], "low_carb": true}}

Example 10:
Query: "2 chicken recipes"
Response: {{"tags": ["mains", "soups", "salads"], "main_protein": "chicken", "exclude_tags": ["beef", "pork", "lamb", "fish"], "result_limit": 2}}

Example 11:
Query: "beef stew under 60 minutes"
Response: {{"tags": ["mains", "soups", "salads"], "main_protein": "beef", "exclude_tags": ["chicken", "pork", "lamb", "fish"], "max_time": 60}}

Example 12:
Query: "vegetarian drinks"
Response: {{"dietary_tags": ["vegetarian"], "tags": ["drinks"]}}

Example 13:
Query: "easy breakfast"
Response: {{"tags": ["breakfast"], "difficulty": ["easy"]}}

Now extract filters for the user query above.
"""

    def _parse_filter_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse Gemini response to extract filters.

        Args:
            response_text: Raw response from Gemini

        Returns:
            Dictionary of filters
        """
        try:
            # Remove markdown code blocks if present
            cleaned = response_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            filters = json.loads(cleaned)
            return filters
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON response: {str(e)}")
            logger.debug(f"Response text: {response_text}")
            return {}

    def detect_ambiguity(self, query: str) -> Optional[str]:
        """
        Detect if a query is ambiguous and suggest clarifying questions.

        Args:
            query: User query

        Returns:
            Clarifying question string or None if query is clear
        """
        # Simple heuristics for ambiguity detection
        vague_terms = ["something", "anything", "good", "nice", "tasty", "yummy", "delicious"]
        query_lower = query.lower()

        # Check if query contains "recipe" or "recipes" without meal type specification
        meal_types = ["breakfast", "lunch", "dinner", "snack", "appetizer", "main", "dessert", "sweet", "drink", "beverage", "soup", "salad", "side"]
        has_recipe_word = "recipe" in query_lower or "recipes" in query_lower
        has_meal_type = any(meal_type in query_lower for meal_type in meal_types)

        # Check for dietary restrictions that might clarify intent
        dietary_indicators = ["vegetarian", "vegan", "gluten", "protein", "low fat", "low carb"]
        has_dietary = any(indicator in query_lower for indicator in dietary_indicators)

        # If query has "recipe(s)" but no meal type and only dietary tags, ask for clarification
        if has_recipe_word and not has_meal_type and has_dietary:
            return "What type of dish are you looking for? (main dishes, soups, salads, side dishes, desserts, drinks)"

        # Check for vague terms without specifics
        has_vague_term = any(term in query_lower for term in vague_terms)
        has_specific_constraint = any(
            term in query_lower
            for term in ["vegetarian", "vegan", "minutes", "quick", "easy", "breakfast", "lunch", "dinner"]
        )

        if has_vague_term and not has_specific_constraint:
            return "What type of dish are you looking for? (main dishes, soups, salads, desserts, drinks)"

        # Check for "quick" without time specification
        if "quick" in query_lower and ("minute" not in query_lower and "hour" not in query_lower):
            return "How much time do you have? (under 15 min, 15-30 min, 30-60 min)"

        # Very short queries
        if len(query.split()) <= 2 and not has_specific_constraint:
            return "Could you be more specific? For example: 'easy vegetarian pasta under 30 minutes'"

        return None


# Global client instance
gemini_client = GeminiClient()
