# This module is intentionally left as a re-export for backward compatibility.
# All connection types should inherit from postgres.base_connection.PostgresBaseConnection.
from pgmonkey.connections.postgres.base_connection import PostgresBaseConnection

__all__ = ['PostgresBaseConnection']
