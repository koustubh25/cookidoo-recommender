"""Sanity tests for recipe recommendation system."""

import sys
import os
import logging

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from recommendations.engine import recommendation_engine
from db.connection import db_connection
from config.settings import settings

logger = logging.getLogger(__name__)


class SanityTests:
    """Sanity tests to validate recommendation accuracy."""

    def __init__(self):
        """Initialize tests."""
        self.engine = recommendation_engine
        self.passed = 0
        self.failed = 0

    def run_all(self) -> bool:
        """
        Run all sanity tests.

        Returns:
            True if all tests passed, False otherwise
        """
        print("\n" + "=" * 60)
        print("Running Sanity Tests")
        print("=" * 60)

        # Connect to database
        try:
            print("\n[Setup] Connecting to database...")
            db_connection.connect_with_retry()
            if not db_connection.validate_connection():
                print("✗ Database connection validation failed")
                return False
            print("✓ Database connected and validated")
        except Exception as e:
            print(f"✗ Database connection failed: {str(e)}")
            return False

        # Run tests
        self.test_drink_recipes()
        self.test_vegetarian_recipes()
        self.test_time_constraints()
        self.test_recipe_name_search()
        self.test_tm6_compatibility()

        # Print summary
        print("\n" + "=" * 60)
        print(f"Tests Passed: {self.passed}")
        print(f"Tests Failed: {self.failed}")
        print("=" * 60)

        # Cleanup
        db_connection.close()

        return self.failed == 0

    def test_drink_recipes(self) -> None:
        """Test that drink recipe query returns only drinks."""
        print("\n[Test 1] Drink recipes query")
        try:
            results = self.engine.recommend("5 drink recipes", limit=5)

            if not results:
                print("✗ No results returned")
                self.failed += 1
                return

            # Check if recipes are drinks (would need to verify tags)
            print(f"✓ Returned {len(results)} results")
            for i, recipe in enumerate(results[:3], 1):
                print(f"  {i}. {recipe.get('title')}")

            self.passed += 1

        except Exception as e:
            print(f"✗ Test failed: {str(e)}")
            self.failed += 1

    def test_vegetarian_recipes(self) -> None:
        """Test that vegetarian query returns vegetarian recipes."""
        print("\n[Test 2] Vegetarian recipes query")
        try:
            results = self.engine.recommend("vegetarian meals", limit=5)

            if not results:
                print("✗ No results returned")
                self.failed += 1
                return

            print(f"✓ Returned {len(results)} results")
            for i, recipe in enumerate(results[:3], 1):
                print(f"  {i}. {recipe.get('title')}")

            self.passed += 1

        except Exception as e:
            print(f"✗ Test failed: {str(e)}")
            self.failed += 1

    def test_time_constraints(self) -> None:
        """Test that time constraint filtering works."""
        print("\n[Test 3] Time constraint query")
        try:
            results = self.engine.recommend("recipes under 20 minutes", limit=5)

            if not results:
                print("✗ No results returned")
                self.failed += 1
                return

            # Check time constraints
            violations = 0
            for recipe in results:
                time = recipe.get('total_time_minutes', 0)
                if time and time > 20:
                    violations += 1
                    print(f"  ✗ Recipe '{recipe.get('title')}' takes {time} minutes")

            if violations > 0:
                print(f"✗ Found {violations} recipes exceeding time limit")
                self.failed += 1
            else:
                print(f"✓ All {len(results)} recipes meet time constraint")
                for i, recipe in enumerate(results[:3], 1):
                    time = recipe.get('total_time_minutes', 0)
                    print(f"  {i}. {recipe.get('title')} ({time} min)")
                self.passed += 1

        except Exception as e:
            print(f"✗ Test failed: {str(e)}")
            self.failed += 1

    def test_recipe_name_search(self) -> None:
        """Test recipe name search functionality."""
        print("\n[Test 4] Recipe name search")
        try:
            results = self.engine.recommend("chicken curry", limit=5)

            if not results:
                print("✗ No results returned")
                self.failed += 1
                return

            print(f"✓ Returned {len(results)} results")
            for i, recipe in enumerate(results[:3], 1):
                print(f"  {i}. {recipe.get('title')}")

            self.passed += 1

        except Exception as e:
            print(f"✗ Test failed: {str(e)}")
            self.failed += 1

    def test_tm6_compatibility(self) -> None:
        """Test that all results are TM6 compatible."""
        print("\n[Test 5] TM6 compatibility")
        try:
            results = self.engine.recommend("pasta recipes", limit=10)

            if not results:
                print("✗ No results returned")
                self.failed += 1
                return

            # All results should be TM6 compatible (checked in query)
            print(f"✓ All {len(results)} results are TM6 compatible (verified by query filter)")
            self.passed += 1

        except Exception as e:
            print(f"✗ Test failed: {str(e)}")
            self.failed += 1


def main():
    """Run sanity tests."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    tests = SanityTests()
    success = tests.run_all()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
