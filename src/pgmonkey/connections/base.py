from abc import ABC, abstractmethod

class BaseConnection(ABC):
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
