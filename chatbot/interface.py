"""Interactive chatbot interface for recipe discovery."""

import sys
import logging
from chatbot.session import ChatSession
from recommendations.engine import recommendation_engine
from ai.gemini_client import gemini_client
from db.connection import db_connection

logger = logging.getLogger(__name__)


class RecipeChatbot:
    """Interactive chatbot for recipe recommendations."""

    def __init__(self):
        """Initialize the chatbot."""
        self.session = ChatSession()
        self.engine = recommendation_engine
        self.ai_client = gemini_client
        self.running = False

    def start(self) -> None:
        """Start the interactive chatbot loop."""
        self.running = True
        self._show_welcome()

        # Initialize database connection
        try:
            print("\n Connecting to database...")
            db_connection.connect_with_retry()
            print("✓ Database connected")

            print("\n Validating connection...")
            if not db_connection.validate_connection():
                print("✗ Connection validation failed. Please check your configuration.")
                return
            print("✓ Connection validated")

        except Exception as e:
            print(f"\n✗ Failed to connect to database: {str(e)}")
            return

        # Main conversation loop
        while self.running:
            try:
                query = input("\nYou: ").strip()

                if not query:
                    continue

                # Handle special commands
                if self._handle_command(query):
                    continue

                # Process regular query
                self._process_query(query)

            except KeyboardInterrupt:
                print("\n\nGoodbye!")
                self.running = False
            except Exception as e:
                logger.error(f"Error processing query: {str(e)}")
                print(f"\n✗ Error: {str(e)}")

        # Cleanup
        print("\nClosing connections...")
        try:
            db_connection.close()
        except Exception as e:
            logger.warning(f"Error during cleanup: {str(e)}")
        print("✓ Cleanup complete")

    def _show_welcome(self) -> None:
        """Display welcome message."""
        print("\n" + "=" * 60)
        print("🍳 Thermomix Recipe Recommendation Assistant")
        print("=" * 60)
        print("\nI can help you discover recipes from your Cookidoo database!")
        print("\nExample queries:")
        print("  - Easy vegetarian dinner under 30 minutes")
        print("  - Quick breakfast recipes")
        print("  - Chocolate desserts")
        print("  - Chicken curry")
        print("\nSpecial commands:")
        print("  /history - View your query history")
        print("  /similar #N - Find recipes similar to result #N from last query")
        print("  /help - Show this help message")
        print("  /quit or /exit - Exit the chatbot")
        print("=" * 60)

    def _handle_command(self, query: str) -> bool:
        """
        Handle special chatbot commands.

        Args:
            query: User input

        Returns:
            True if command was handled, False otherwise
        """
        query_lower = query.lower()

        if query_lower in ["/quit", "/exit"]:
            print("\nGoodbye!")
            self.running = False
            return True

        if query_lower == "/help":
            self._show_welcome()
            return True

        if query_lower == "/history":
            print(self.session.get_history_summary())
            return True

        if query_lower.startswith("/similar"):
            parts = query.split()
            if len(parts) >= 2 and parts[1].startswith("#"):
                try:
                    index = int(parts[1][1:])
                    self._find_similar(index)
                except ValueError:
                    print("✗ Invalid index. Use format: /similar #N")
            else:
                print("✗ Usage: /similar #N (e.g., /similar #2)")
            return True

        return False

    def _process_query(self, query: str) -> None:
        """
        Process a recipe query.

        Args:
            query: User query string
        """
        # Check if this is a refinement of the previous query
        context, previous_filters = self.session.get_context_for_query(query)
        enhanced_query = query

        if context:
            # Combine previous query with current refinement
            enhanced_query = f"{context} {query}"
            print(f"\nBot: I'll refine your previous search...")
            print(f"     Previous: '{context}'")
            print(f"     Adding: '{query}'")
        else:
            # Check for ambiguity only for new queries
            clarification = self.ai_client.detect_ambiguity(query)
            if clarification:
                print(f"\nBot: {clarification}")
                print("\nOr type your query again to proceed with a broad search.")
                return

        print("\nBot: Searching for recipes...")

        try:
            # Get recommendations with context-aware filters
            results, filters = self.engine.recommend(
                enhanced_query,
                previous_filters=previous_filters
            )

            if not results:
                print("\n✗ No recipes found matching your criteria.")
                print("Try broadening your search or using different keywords.")
                return

            # Store the query, results, and merged filters in session
            self.session.add_query(
                enhanced_query if context else query,
                results,
                filters
            )

            # Display results
            print(f"\nFound {len(results)} recipes:\n")
            for i, recipe in enumerate(results, 1):
                self._display_recipe(recipe, i)

            # Show how to open recipes
            print("\nTo view a recipe on Cookidoo, copy and paste the URL into your browser.")
            print("Or use /similar #N to find recipes similar to result #N")

        except Exception as e:
            logger.error(f"Query processing failed: {str(e)}")
            print(f"\n✗ Sorry, something went wrong: {str(e)}")

    def _display_recipe(self, recipe: dict, index: int) -> None:
        """
        Display a recipe in the chatbot.

        Args:
            recipe: Recipe dictionary
            index: Result index number
        """
        print(f"\n[#{index}] {recipe.get('title', 'Unknown Recipe')}")
        print(f"    URL: {recipe.get('url', 'N/A')}")

        image_url = recipe.get('image_url')
        if image_url:
            print(f"    Image: {image_url}")

        rating = recipe.get('rating')
        rating_count = recipe.get('rating_count')
        if rating and rating_count:
            print(f"    Rating: {rating:.1f}/5.0 ({rating_count} reviews)")

        total_time = recipe.get('total_time_minutes')
        if total_time:
            print(f"    Time: {total_time} minutes")

        difficulty = recipe.get('difficulty')
        if difficulty:
            print(f"    Difficulty: {difficulty}")

        # Display per-serving nutrition if available
        servings = recipe.get('servings')
        calories_per_serving = recipe.get('calories_per_serving')
        protein_per_serving = recipe.get('protein_per_serving')
        carbs_per_serving = recipe.get('carbs_per_serving')
        fat_per_serving = recipe.get('fat_per_serving')

        if servings and any([calories_per_serving, protein_per_serving, carbs_per_serving, fat_per_serving]):
            nutrition_parts = []
            if calories_per_serving:
                nutrition_parts.append(f"{calories_per_serving:.0f} kcal")
            if protein_per_serving:
                nutrition_parts.append(f"{protein_per_serving:.1f}g protein")
            if carbs_per_serving:
                nutrition_parts.append(f"{carbs_per_serving:.1f}g carbs")
            if fat_per_serving:
                nutrition_parts.append(f"{fat_per_serving:.1f}g fat")

            if nutrition_parts:
                print(f"    Nutrition (per serving, {servings} servings): {', '.join(nutrition_parts)}")

    def _find_similar(self, index: int) -> None:
        """
        Find recipes similar to a previous result.

        Args:
            index: Index of the recipe from last results (1-based)
        """
        last_results = self.session.get_last_results()
        if not last_results:
            print("✗ No previous results to reference.")
            return

        if index < 1 or index > len(last_results):
            print(f"✗ Invalid index. Please use a number between 1 and {len(last_results)}")
            return

        reference_recipe = last_results[index - 1]
        recipe_id = reference_recipe.get("recipe_id")
        recipe_title = reference_recipe.get("title", "Unknown")

        print(f"\nBot: Finding recipes similar to '{recipe_title}'...")

        try:
            results = self.engine.get_similar_recipes(recipe_id)

            if not results:
                print("\n✗ No similar recipes found.")
                return

            # Store in session
            query = f"Similar to: {recipe_title}"
            self.session.add_query(query, results)

            # Display results
            print(f"\nFound {len(results)} similar recipes:\n")
            for i, recipe in enumerate(results, 1):
                self._display_recipe(recipe, i)

        except Exception as e:
            logger.error(f"Similar recipe search failed: {str(e)}")
            print(f"\n✗ Sorry, something went wrong: {str(e)}")


def main():
    """Main entry point for the chatbot."""
    # Set up logging with DEBUG level for verbose connection debugging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('chatbot.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Start chatbot
    chatbot = RecipeChatbot()
    chatbot.start()


if __name__ == "__main__":
    main()
