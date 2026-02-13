from abc import ABC, abstractmethod


class PostgresBaseConnection(ABC):
    """Abstract base class defining the interface for all PostgreSQL connection types."""

    @abstractmethod
    def connect(self):
        """Establish a database connection."""
        pass

    @abstractmethod
    def test_connection(self):
        """Test the database connection."""
        pass

    @abstractmethod
    def disconnect(self):
        """Close the database connection."""
        pass

    @abstractmethod
    def commit(self):
        """Commit the current transaction."""
        pass

    @abstractmethod
    def rollback(self):
        """Rollback the current transaction."""
        pass

    @abstractmethod
    def cursor(self):
        """Create and return a cursor object."""
        pass
