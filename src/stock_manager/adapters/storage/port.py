"""
Storage Adapter Port

Defines the interface for database operations.
Following hexagonal architecture pattern for dependency inversion.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class DatabasePort(ABC):
    """Database adapter port

    Abstract interface for database operations. Concrete implementations
    (e.g., PostgreSQL, SQLite) will implement this port.
    """

    @abstractmethod
    def execute_query(
        self,
        query: str,
        params: Optional[tuple] = None,
        fetch_one: bool = False,
        fetch_all: bool = False,
    ) -> Optional[Any]:
        """Execute a SQL query

        Args:
            query: SQL query string
            params: Query parameters
            fetch_one: Return single row (dict)
            fetch_all: Return all rows (list of dict)

        Returns:
            Query result (dict, list of dict, or None)
        """
        pass

    @abstractmethod
    def execute_transaction(
        self,
        queries: list[tuple[str, Optional[tuple]]],
    ) -> bool:
        """Execute multiple queries in a transaction

        Args:
            queries: List of (query, params) tuples

        Returns:
            bool: True if transaction succeeded
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """Close database connection"""
        pass
