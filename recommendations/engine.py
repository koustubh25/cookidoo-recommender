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
        skip_filter_extraction: bool = False,
        previous_filters: Optional[Dict[str, Any]] = None
    ) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Get recipe recommendations for a natural language query.

        Implements two-stage hybrid search:
        1. Extract structured filters using Gemini
        2. Perform vector similarity search with filters

        Args:
            query: Natural language recipe query
            limit: Maximum number of results
            skip_filter_extraction: If True, skip NL2SQL and use pure vector search
            previous_filters: Filters from previous query (for context-aware refinement)

        Returns:
            Tuple of (list of ranked recipe dictionaries, merged filters dict)
        """
        logger.info("="*80)
        logger.info(f"PROCESSING RECOMMENDATION QUERY: '{query}'")
        logger.info(f"Skip filter extraction: {skip_filter_extraction}")
        logger.info(f"Limit parameter: {limit}")
        logger.info(f"Previous filters: {previous_filters}")
        logger.info("="*80)

        # Detect if query should prioritize ratings
        prioritize_ratings = self._should_prioritize_ratings(query)
        logger.info(f"Prioritize ratings: {prioritize_ratings}")

        # Stage 1: Extract structured filters (unless skipped)
        filters = {}
        if not skip_filter_extraction:
            try:
                logger.info("Calling Gemini to extract filters...")
                filters = self.ai_client.extract_filters(query)
                logger.info(f"✓ Extracted filters: {filters}")
            except Exception as e:
                logger.warning(f"✗ Filter extraction failed, falling back to pure vector search: {str(e)}")
                logger.exception("Filter extraction error details:")
                filters = {}
        else:
            logger.info("Skipping filter extraction (skip_filter_extraction=True)")

        # Add minimum rating filters for quality-focused queries
        if prioritize_ratings and "min_rating" not in filters:
            filters["min_rating"] = 4.0
            filters["min_rating_count"] = 10
            logger.info(f"Quality-focused query detected - adding min_rating=4.0, min_rating_count=10")

        # Merge with previous filters if provided
        if previous_filters:
            logger.info(f"Merging with previous filters: {previous_filters}")
            merged_filters = self._merge_filters(previous_filters, filters)
            logger.info(f"✓ Merged filters: {merged_filters}")
            filters = merged_filters

        # Extract result limit from filters if present
        extracted_limit = filters.pop("result_limit", None) if filters else None
        user_requested_limit = limit or extracted_limit or settings.RESULT_LIMIT

        # For quality-focused queries, fetch MANY more candidates to ensure we get the best ones
        # Vector similarity alone may not surface the highest-rated recipes
        # We'll fetch 50x the requested amount (minimum 50), then rank by rating and return top N
        if prioritize_ratings:
            search_limit = max(user_requested_limit * 50, 50)  # At least 50 candidates
            logger.info(f"Quality-focused query - expanding search limit from {user_requested_limit} to {search_limit}")
            logger.info(f"This ensures highly-rated recipes are included even with lower semantic similarity")
        else:
            search_limit = user_requested_limit

        logger.info("="*80)
        logger.info(f"LIMIT RESOLUTION:")
        logger.info(f"  Limit parameter: {limit}")
        logger.info(f"  Extracted limit: {extracted_limit}")
        logger.info(f"  User requested limit: {user_requested_limit}")
        logger.info(f"  Search limit (for vector search): {search_limit}")
        logger.info(f"FILTERS AFTER LIMIT EXTRACTION: {filters}")
        logger.info("="*80)

        # Generate query embedding
        try:
            embedding = self.ai_client.generate_embedding(query)
        except Exception as e:
            logger.error(f"Embedding generation failed: {str(e)}")
            raise

        # Stage 2: Vector similarity search with filters
        # Pass prioritize_ratings flag to change database ordering
        try:
            results = self.queries.vector_similarity_search(
                embedding=embedding,
                filters=filters if filters else None,
                limit=search_limit,
                prioritize_ratings=prioritize_ratings
            )
        except Exception as e:
            logger.error(f"Vector search failed: {str(e)}")
            raise

        # Rank results (pass prioritize_ratings flag for dynamic weighting)
        ranked_results = self._rank_results(results, prioritize_ratings=prioritize_ratings)

        # For quality-focused queries, we fetched more candidates - now trim to user's requested limit
        if prioritize_ratings and len(ranked_results) > user_requested_limit:
            logger.info(f"Trimming {len(ranked_results)} results to top {user_requested_limit} after ranking")
            ranked_results = ranked_results[:user_requested_limit]

        logger.info(f"Returning {len(ranked_results)} recommendations")
        return ranked_results, filters

    def _should_prioritize_ratings(self, query: str) -> bool:
        """
        Detect if query should prioritize ratings over semantic similarity.

        Returns True for:
        1. Quality-focused queries (best, top, highest rated, etc.)
        2. Vague queries without specific semantic intent

        Args:
            query: User query string

        Returns:
            True if ratings should be prioritized
        """
        query_lower = query.lower().strip()

        # Quality-focused keywords that explicitly ask for highly-rated recipes
        quality_keywords = [
            "best", "top", "highest rated", "highly rated", "top rated",
            "most popular", "popular", "favorite", "favourite", "recommend"
        ]

        # Vague descriptors without quality focus
        vague_terms = ["good", "nice", "great", "some", "any", "something"]

        # Specific attributes that provide clear semantic intent
        specific_terms = [
            # Proteins
            "chicken", "beef", "pork", "fish", "lamb", "turkey", "seafood",
            # Dietary
            "vegetarian", "vegan", "gluten", "dairy",
            # Cuisine
            "italian", "indian", "chinese", "mexican", "thai", "french", "japanese",
            # Meal types (explicit)
            "breakfast", "lunch", "dinner", "dessert", "snack", "appetizer",
            # Specific dishes
            "pasta", "pizza", "curry", "soup", "salad", "rice", "stew", "cake",
            # Cooking methods
            "grilled", "baked", "fried", "roasted", "steamed",
            # Time constraints
            "quick", "fast", "slow", "minutes", "hour",
            # Difficulty
            "easy", "simple", "hard", "difficult", "beginner"
        ]

        # Check for quality-focused keywords (always prioritize ratings for these)
        has_quality_keyword = any(keyword in query_lower for keyword in quality_keywords)
        if has_quality_keyword:
            return True

        # Check for vague queries without specific terms
        has_vague_term = any(term in query_lower for term in vague_terms)
        has_specific_term = any(term in query_lower for term in specific_terms)
        word_count = len(query_lower.split())

        # Vague if:
        # 1. Has vague terms AND no specific terms, OR
        # 2. Very short (≤4 words) and contains only generic words
        is_vague = (has_vague_term and not has_specific_term) or (word_count <= 4 and not has_specific_term)

        return is_vague

    def _merge_filters(self, previous: Dict[str, Any], current: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge previous filters with current filters intelligently.

        Rules:
        - Current filters override previous for scalar values
        - List filters (tags, dietary_tags, cuisine) are merged (union)
        - New main_protein replaces old one and updates exclude_tags
        - Boolean filters from current override previous

        Args:
            previous: Previous query filters
            current: Current query filters

        Returns:
            Merged filter dictionary
        """
        merged = previous.copy()

        # List fields that should be merged (union)
        list_fields = ["tags", "dietary_tags", "cuisine"]

        for key, value in current.items():
            if key in list_fields and key in merged:
                # Merge lists (union without duplicates)
                merged[key] = list(set(merged[key] + value))
            elif key == "main_protein":
                # New protein replaces old one
                merged[key] = value
                # Update exclude_tags based on new protein
                if "exclude_tags" in current:
                    merged["exclude_tags"] = current["exclude_tags"]
            else:
                # For all other fields (including result_limit, max_time, etc.), current overrides
                merged[key] = value

        return merged

    def _rank_results(self, results: List[Dict[str, Any]], prioritize_ratings: bool = False) -> List[Dict[str, Any]]:
        """
        Rank results using weighted scoring with Bayesian average for ratings.

        Uses Bayesian average to give more weight to recipes with more reviews.
        Dynamically adjusts weights based on query intent:
        - Quality-focused or vague queries: similarity 20%, bayesian_rating 80%
          Examples: "best chicken recipes", "give me some good recipes"
        - Specific semantic queries: similarity 60%, bayesian_rating 40%
          Examples: "chicken curry", "easy Italian pasta"

        Args:
            results: List of search results with similarity scores
            prioritize_ratings: Whether to prioritize ratings over semantic similarity

        Returns:
            Sorted list of results with ranking scores
        """
        if not results:
            return []

        # Dynamic weight adjustment based on query intent
        if prioritize_ratings:
            similarity_weight = 0.2
            rating_weight = 0.8
            logger.info("Prioritizing ratings - Using weights: similarity=0.2, rating=0.8")
        else:
            similarity_weight = settings.SIMILARITY_WEIGHT
            rating_weight = settings.RATING_WEIGHT + settings.RATING_COUNT_WEIGHT
            logger.info(f"Balanced mode - Using weights: similarity={similarity_weight}, rating={rating_weight}")

        # Calculate global average rating and confidence threshold
        # These values help penalize recipes with few reviews
        all_ratings = [(r.get("rating") or 0, r.get("rating_count") or 0) for r in results]
        total_reviews = sum(count for _, count in all_ratings)
        if total_reviews > 0:
            global_avg_rating = sum(rating * count for rating, count in all_ratings) / total_reviews
        else:
            global_avg_rating = 3.0  # Default if no ratings

        # Confidence threshold: minimum number of reviews to trust the rating
        # Use 10th percentile of rating_count as confidence threshold
        rating_counts = sorted([count for _, count in all_ratings if count > 0])
        if rating_counts:
            confidence_threshold = rating_counts[max(0, len(rating_counts) // 10)]
        else:
            confidence_threshold = 5  # Default minimum

        for result in results:
            similarity_score = result.get("similarity_score", 0)
            rating = result.get("rating") or 0
            rating_count = result.get("rating_count") or 0

            # Calculate Bayesian average (weighted rating)
            # Formula: (C * m + R * v) / (C + v)
            # Where: C = confidence threshold, m = global average, R = recipe rating, v = review count
            if rating_count > 0:
                bayesian_rating = (
                    (confidence_threshold * global_avg_rating + rating * rating_count) /
                    (confidence_threshold + rating_count)
                )
            else:
                bayesian_rating = global_avg_rating  # No reviews = global average

            # Normalize Bayesian rating to 0-1 scale (assuming max rating is 5.0)
            normalized_bayesian_rating = bayesian_rating / 5.0

            # Calculate weighted ranking score using dynamic weights
            rank_score = (
                similarity_score * similarity_weight +
                normalized_bayesian_rating * rating_weight
            )

            result["rank_score"] = rank_score
            result["bayesian_rating"] = bayesian_rating

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
