"""Recipe recommendation engine with hybrid search and ranking."""

import logging
from typing import List, Dict, Any, Optional
from ai.gemini_client import gemini_client
from db.queries import RecipeQueries
from config.settings import settings

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """Orchestrates hybrid search and result ranking for recipe recommendations."""

    def __init__(self):
        """Initialize the recommendation engine."""
        self.ai_client = gemini_client
        self.queries = RecipeQueries()

    def recommend(
        self,
        query: str,
        limit: Optional[int] = None,
        skip_filter_extraction: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get recipe recommendations for a natural language query.

        Implements two-stage hybrid search:
        1. Extract structured filters using Gemini
        2. Perform vector similarity search with filters

        Args:
            query: Natural language recipe query
            limit: Maximum number of results
            skip_filter_extraction: If True, skip NL2SQL and use pure vector search

        Returns:
            List of ranked recipe dictionaries
        """
        logger.info(f"Processing recommendation query: {query}")

        # Stage 1: Extract structured filters (unless skipped)
        filters = {}
        if not skip_filter_extraction:
            try:
                filters = self.ai_client.extract_filters(query)
                logger.info(f"Extracted filters: {filters}")
            except Exception as e:
                logger.warning(f"Filter extraction failed, falling back to pure vector search: {str(e)}")
                filters = {}

        # Generate query embedding
        try:
            embedding = self.ai_client.generate_embedding(query)
        except Exception as e:
            logger.error(f"Embedding generation failed: {str(e)}")
            raise

        # Stage 2: Vector similarity search with filters
        try:
            results = self.queries.vector_similarity_search(
                embedding=embedding,
                filters=filters if filters else None,
                limit=limit if limit else settings.RESULT_LIMIT
            )
        except Exception as e:
            logger.error(f"Vector search failed: {str(e)}")
            raise

        # Rank results
        ranked_results = self._rank_results(results)

        logger.info(f"Returning {len(ranked_results)} recommendations")
        return ranked_results

    def _rank_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Rank results using weighted scoring.

        Ranking formula: (similarity * 0.6) + (normalized_rating * 0.3) + (normalized_rating_count * 0.1)

        Args:
            results: List of search results with similarity scores

        Returns:
            Sorted list of results with ranking scores
        """
        if not results:
            return []

        # Find max values for normalization
        max_rating = max((r.get("rating") or 0) for r in results)
        max_rating_count = max((r.get("rating_count") or 0) for r in results)

        for result in results:
            similarity_score = result.get("similarity_score", 0)
            rating = result.get("rating") or 0
            rating_count = result.get("rating_count") or 0

            # Normalize rating and rating_count to 0-1 range
            normalized_rating = rating / max_rating if max_rating > 0 else 0
            normalized_rating_count = rating_count / max_rating_count if max_rating_count > 0 else 0

            # Calculate weighted ranking score
            rank_score = (
                similarity_score * settings.SIMILARITY_WEIGHT +
                normalized_rating * settings.RATING_WEIGHT +
                normalized_rating_count * settings.RATING_COUNT_WEIGHT
            )

            result["rank_score"] = rank_score

        # Sort by rank score (descending)
        ranked = sorted(results, key=lambda x: x.get("rank_score", 0), reverse=True)

        return ranked

    def format_recipe(self, recipe: Dict[str, Any]) -> str:
        """
        Format a recipe for display in chatbot.

        Args:
            recipe: Recipe dictionary

        Returns:
            Formatted string representation
        """
        title = recipe.get("title", "Unknown Recipe")
        url = recipe.get("url", "")
        image_url = recipe.get("image_url", "")
        rating = recipe.get("rating", 0)
        rating_count = recipe.get("rating_count", 0)
        total_time = recipe.get("total_time_minutes", 0)
        difficulty = recipe.get("difficulty", "Unknown")
        rank_score = recipe.get("rank_score", 0)

        # Format output
        output = f"\n{'='*60}\n"
        output += f"Recipe: {title}\n"
        output += f"URL: {url}\n"

        if image_url:
            output += f"Image: {image_url}\n"

        if rating and rating_count:
            output += f"Rating: {rating:.1f}/5.0 ({rating_count} reviews)\n"

        if total_time:
            output += f"Time: {total_time} minutes\n"

        output += f"Difficulty: {difficulty}\n"
        output += f"Relevance Score: {rank_score:.3f}\n"
        output += f"{'='*60}\n"

        return output

    def get_similar_recipes(
        self,
        recipe_id: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Find recipes similar to a given recipe.

        Args:
            recipe_id: ID of the reference recipe
            limit: Maximum number of similar recipes

        Returns:
            List of similar recipes
        """
        # Fetch the reference recipe
        reference_recipe = self.queries.get_recipe_by_id(recipe_id)
        if not reference_recipe:
            logger.warning(f"Recipe {recipe_id} not found")
            return []

        # Use the recipe title as query for finding similar recipes
        query = reference_recipe.get("title", "")
        return self.recommend(query, limit=limit, skip_filter_extraction=True)


# Global engine instance
recommendation_engine = RecommendationEngine()
