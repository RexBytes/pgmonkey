from abc import ABC, abstractmethod
from ..base import BaseConnection  # Assuming base.py contains BaseConnection and is in the same directory level


class PostgresBaseConnection(BaseConnection, ABC):
    # PostgreSQL-specific shared behavior (if any)
    pass
