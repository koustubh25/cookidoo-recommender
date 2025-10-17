"""Database query operations for recipe search."""

import logging
from typing import List, Dict, Any, Optional
from db.connection import db_connection
from config.settings import settings

logger = logging.getLogger(__name__)


class RecipeQueries:
    """Handles database queries for recipe recommendations."""

    @staticmethod
    def build_where_clause(filters: Dict[str, Any]) -> tuple[str, list]:
        """
        Build SQL WHERE clause from extracted filters.

        Args:
            filters: Dictionary of filter conditions

        Returns:
            Tuple of (WHERE clause string, list of parameters)
        """
        conditions = []
        params = []

        logger.info("="*80)
        logger.info("BUILDING WHERE CLAUSE")
        logger.info(f"Input filters: {filters}")
        logger.info("="*80)

        # Always filter by TM6 compatibility
        conditions.append("rtv.version = %s")
        params.append(settings.THERMOMIX_VERSION)
        logger.debug(f"Added TM6 filter: version = {settings.THERMOMIX_VERSION}")

        # Dietary tags filter (case-insensitive)
        if "dietary_tags" in filters and filters["dietary_tags"]:
            logger.info(f"Processing dietary_tags filter: {filters['dietary_tags']}")
            # Use ILIKE for case-insensitive matching
            dietary_conditions = []
            for dietary_tag in filters["dietary_tags"]:
                dietary_conditions.append("dietary_tag ILIKE %s")
                pattern = f"%{dietary_tag}%"
                params.append(pattern)
                logger.info(f"  Added dietary tag pattern: {pattern}")

            dietary_clause = " OR ".join(dietary_conditions)
            dietary_sql = f"""
                r.recipe_id IN (
                    SELECT recipe_id FROM recipe_dietary_tags
                    WHERE {dietary_clause}
                )
            """
            conditions.append(dietary_sql)
            logger.info(f"  Dietary SQL clause: {dietary_sql}")
            logger.info(f"  Dietary params: {[p for p in params if '%' in str(p)]}")

        # Tags filter (meal type, etc.) - case-insensitive
        if "tags" in filters and filters["tags"]:
            # Use ILIKE for case-insensitive matching
            tag_conditions = []
            for tag in filters["tags"]:
                tag_conditions.append("tag ILIKE %s")
                params.append(f"%{tag}%")

            tag_clause = " OR ".join(tag_conditions)
            conditions.append(f"""
                r.recipe_id IN (
                    SELECT recipe_id FROM recipe_tags
                    WHERE {tag_clause}
                )
            """)

        # Time constraints
        if "max_time" in filters:
            conditions.append("r.total_time_minutes <= %s")
            params.append(filters["max_time"])

        if "min_time" in filters:
            conditions.append("r.total_time_minutes >= %s")
            params.append(filters["min_time"])

        # Difficulty filter
        if "difficulty" in filters and filters["difficulty"]:
            difficulty_placeholders = ", ".join(["%s"] * len(filters["difficulty"]))
            conditions.append(f"r.difficulty IN ({difficulty_placeholders})")
            params.extend(filters["difficulty"])

        # Recipe name search (ILIKE pattern matching)
        if "recipe_name" in filters and filters["recipe_name"]:
            conditions.append("r.title ILIKE %s")
            params.append(f"%{filters['recipe_name']}%")

        # Ingredient filter
        if "ingredients" in filters and filters["ingredients"]:
            for ingredient in filters["ingredients"]:
                conditions.append("""
                    r.recipe_id IN (
                        SELECT recipe_id FROM recipe_ingredients
                        WHERE ingredient ILIKE %s
                    )
                """)
                params.append(f"%{ingredient}%")

        # Nutritional filters
        if "high_protein" in filters and filters["high_protein"]:
            # High protein: > 20g per serving
            conditions.append("r.nutrition_protein_g > %s")
            params.append(20)

        if "low_fat" in filters and filters["low_fat"]:
            # Low fat: < 10g per serving
            conditions.append("r.nutrition_fat_g < %s")
            params.append(10)

        if "low_carb" in filters and filters["low_carb"]:
            # Low carb: < 30g per serving
            conditions.append("r.nutrition_carbs_g < %s")
            params.append(30)

        if "low_calorie" in filters and filters["low_calorie"]:
            # Low calorie: < 300 kcal per serving
            conditions.append("r.nutrition_calories_kcal < %s")
            params.append(300)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        logger.info("="*80)
        logger.info("FINAL WHERE CLAUSE:")
        logger.info(f"SQL: {where_clause}")
        logger.info(f"Params: {params}")
        logger.info("="*80)

        return where_clause, params

    @staticmethod
    def vector_similarity_search(
        embedding: List[float],
        filters: Optional[Dict[str, Any]] = None,
        limit: int = None
    ) -> List[Dict[str, Any]]:
        """
        Perform vector similarity search with optional filters.

        Args:
            embedding: Query embedding vector (768-dimensional)
            filters: Optional filter dictionary
            limit: Maximum number of results (default from settings)

        Returns:
            List of recipe dictionaries with similarity scores
        """
        if limit is None:
            limit = settings.RESULT_LIMIT

        # Build WHERE clause from filters
        where_clause = "1=1"
        params = []
        if filters:
            where_clause, params = RecipeQueries.build_where_clause(filters)

        # Convert embedding to PostgreSQL vector format
        embedding_str = "[" + ",".join(map(str, embedding)) + "]"

        query = f"""
            SELECT DISTINCT ON (r.recipe_id)
                r.recipe_id,
                r.title,
                r.url,
                r.prep_time_minutes,
                r.cook_time_minutes,
                r.total_time_minutes,
                r.servings,
                r.difficulty,
                r.nutrition_calories_kcal,
                r.nutrition_protein_g,
                r.nutrition_carbs_g,
                r.nutrition_fat_g,
                r.rating,
                r.rating_count,
                r.image_url,
                (r.embedding <-> %s::vector) AS similarity_distance,
                (1 - (r.embedding <-> %s::vector)) AS similarity_score
            FROM recipes r
            JOIN recipe_thermomix_versions rtv ON r.recipe_id = rtv.recipe_id
            WHERE {where_clause}
            AND r.embedding IS NOT NULL
            ORDER BY r.recipe_id, r.embedding <-> %s::vector
            LIMIT %s;
        """

        try:
            conn = db_connection.get_connection()
            cursor = conn.cursor()

            # Embedding is used 3 times in the query
            query_params = [embedding_str, embedding_str] + params + [embedding_str, limit]

            logger.info("="*80)
            logger.info("EXECUTING VECTOR SEARCH QUERY")
            logger.info("="*80)
            logger.info(f"Full SQL Query:\n{query}")
            logger.info(f"Query params (non-embedding): {params}")
            logger.info(f"Result limit: {limit}")
            logger.info("="*80)

            cursor.execute(query, query_params)
            results = cursor.fetchall()

            # Convert to list of dictionaries
            columns = [desc[0] for desc in cursor.description]
            recipes = [dict(zip(columns, row)) for row in results]

            logger.info("="*80)
            logger.info(f"QUERY RESULTS: {len(recipes)} recipes returned")
            if recipes:
                logger.info("Sample results:")
                for i, recipe in enumerate(recipes[:3], 1):
                    recipe_id = recipe.get('recipe_id')
                    logger.info(f"  {i}. {recipe.get('title')} (ID: {recipe_id}, Similarity: {recipe.get('similarity_score', 0):.3f})")

                    # Verify dietary tags for debugging
                    verify_cursor = conn.cursor()
                    verify_cursor.execute(
                        "SELECT dietary_tag FROM recipe_dietary_tags WHERE recipe_id = %s",
                        (recipe_id,)
                    )
                    dietary_tags = [row[0] for row in verify_cursor.fetchall()]
                    verify_cursor.close()
                    logger.info(f"     Dietary tags: {dietary_tags}")
            logger.info("="*80)

            cursor.close()
            db_connection.return_connection(conn)

            return recipes

        except Exception as e:
            logger.error(f"Vector similarity search failed: {str(e)}")
            raise

    @staticmethod
    def get_recipe_by_id(recipe_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch a single recipe by ID.

        Args:
            recipe_id: Recipe identifier

        Returns:
            Recipe dictionary or None if not found
        """
        query = """
            SELECT
                r.recipe_id,
                r.title,
                r.url,
                r.prep_time_minutes,
                r.cook_time_minutes,
                r.total_time_minutes,
                r.servings,
                r.difficulty,
                r.nutrition_calories_kcal,
                r.nutrition_protein_g,
                r.nutrition_carbs_g,
                r.nutrition_fat_g,
                r.rating,
                r.rating_count,
                r.image_url
            FROM recipes r
            WHERE r.recipe_id = %s;
        """

        try:
            conn = db_connection.get_connection()
            cursor = conn.cursor()

            cursor.execute(query, (recipe_id,))
            result = cursor.fetchone()

            if result:
                columns = [desc[0] for desc in cursor.description]
                recipe = dict(zip(columns, result))
            else:
                recipe = None

            cursor.close()
            db_connection.return_connection(conn)

            return recipe

        except Exception as e:
            logger.error(f"Failed to fetch recipe {recipe_id}: {str(e)}")
            raise
