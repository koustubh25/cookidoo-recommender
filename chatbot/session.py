"""Session management for chatbot conversations."""

import logging
from typing import List, Dict, Any, Optional
from collections import deque
from config.settings import settings

logger = logging.getLogger(__name__)


class ChatSession:
    """Manages conversation history and session state."""

    def __init__(self, max_history: int = None):
        """
        Initialize chat session.

        Args:
            max_history: Maximum number of queries to store (default from settings)
        """
        self.max_history = max_history or settings.SESSION_MEMORY_SIZE
        self.query_history: deque = deque(maxlen=self.max_history)
        self.result_history: deque = deque(maxlen=self.max_history)
        self.filter_history: deque = deque(maxlen=self.max_history)
        logger.info(f"Chat session initialized with max history: {self.max_history}")

    def add_query(self, query: str, results: List[Dict[str, Any]], filters: Optional[Dict[str, Any]] = None) -> None:
        """
        Add a query and its results to session history.

        Args:
            query: User query string
            results: List of recipe results
            filters: Extracted filters from the query
        """
        self.query_history.append(query)
        self.result_history.append(results)
        self.filter_history.append(filters or {})
        logger.debug(f"Added query to history. Total queries: {len(self.query_history)}")

    def get_last_query(self) -> Optional[str]:
        """Get the most recent query."""
        return self.query_history[-1] if self.query_history else None

    def get_last_results(self) -> Optional[List[Dict[str, Any]]]:
        """Get results from the most recent query."""
        return self.result_history[-1] if self.result_history else None

    def get_last_filters(self) -> Optional[Dict[str, Any]]:
        """Get filters from the most recent query."""
        return self.filter_history[-1] if self.filter_history else None

    def get_context_for_query(self, current_query: str) -> tuple[Optional[str], Optional[Dict[str, Any]]]:
        """
        Get context from previous query if current query is a refinement.

        Args:
            current_query: The current user query

        Returns:
            Tuple of (context query string, previous filters dict) or (None, None)
        """
        if not self.query_history:
            return None, None

        last_query = self.get_last_query()
        last_filters = self.get_last_filters()
        current_lower = current_query.lower()

        # Detect refinement keywords
        refinement_keywords = [
            "under", "less than", "more than", "faster", "quicker",
            "easier", "harder", "with", "without", "also", "but",
            "i want", "give me", "show me", "find me"
        ]

        # Detect if query mentions specific additions (chicken, beef, etc.)
        additive_patterns = [
            "chicken", "beef", "pork", "fish", "lamb", "turkey", "seafood",
            "vegetarian", "vegan", "gluten", "pasta", "rice", "pizza"
        ]

        # Check if current query is a refinement
        # Refinement if: short query OR contains refinement keywords OR additive pattern
        is_refinement = (
            (len(current_query.split()) <= 8 and
             any(keyword in current_lower for keyword in refinement_keywords)) or
            (len(current_query.split()) <= 6 and
             any(pattern in current_lower for pattern in additive_patterns))
        )

        if is_refinement:
            logger.info(f"Detected refinement query. Previous: '{last_query}' Current: '{current_query}'")
            return last_query, last_filters

        return None, None

    def get_query_by_index(self, index: int) -> Optional[str]:
        """
        Get query by index (1-based, where 1 is oldest).

        Args:
            index: 1-based index

        Returns:
            Query string or None if index out of range
        """
        try:
            return list(self.query_history)[index - 1]
        except IndexError:
            return None

    def get_results_by_index(self, index: int) -> Optional[List[Dict[str, Any]]]:
        """
        Get results by index (1-based, where 1 is oldest).

        Args:
            index: 1-based index

        Returns:
            Results list or None if index out of range
        """
        try:
            return list(self.result_history)[index - 1]
        except IndexError:
            return None

    def get_history_summary(self) -> str:
        """
        Get a formatted summary of query history.

        Returns:
            Formatted string with query history
        """
        if not self.query_history:
            return "No previous queries in this session."

        summary = "\nQuery History:\n"
        summary += "-" * 60 + "\n"
        for i, query in enumerate(self.query_history, 1):
            summary += f"{i}. {query}\n"
        summary += "-" * 60 + "\n"

        return summary

    def clear(self) -> None:
        """Clear session history."""
        self.query_history.clear()
        self.result_history.clear()
        logger.info("Session history cleared")

    def __len__(self) -> int:
        """Return number of queries in history."""
        return len(self.query_history)
