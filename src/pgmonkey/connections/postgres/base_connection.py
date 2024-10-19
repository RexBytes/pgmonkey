from abc import ABC, abstractmethod

class PostgresBaseConnection(ABC):
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
        """Create and return a cursor object, which can be used to perform database operations."""
        pass

    def __enter__(self):
        try:
            self.connect()
        except Exception as e:
            # Handle or log exception as necessary
            raise RuntimeError(f"Failed to establish database connection: {e}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.disconnect()
        except Exception as e:
            # Handle or log disconnection errors
            raise RuntimeError(f"Failed to close database connection properly: {e}")

