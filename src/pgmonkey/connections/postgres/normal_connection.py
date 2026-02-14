import logging
from psycopg import connect, OperationalError
from .base_connection import PostgresBaseConnection
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class PGNormalConnection(PostgresBaseConnection):
    def __init__(self, config):
        self.config = config
        self.connection = None

    def connect(self):
        if self.connection is None or self.connection.closed:
            self.connection = connect(**self.config)

    def test_connection(self):
        try:
            with self.cursor() as cur:
                cur.execute('SELECT 1;')
                result = cur.fetchone()
                logger.info("Connection successful: %s", result)
        except OperationalError as e:
            logger.error("Connection failed: %s", e)
        except Exception as e:
            logger.error("An unexpected error occurred: %s", e)

    def disconnect(self):
        if self.connection and not self.connection.closed:
            self.connection.close()
            self.connection = None

    def commit(self):
        if self.connection:
            self.connection.commit()

    def rollback(self):
        if self.connection:
            self.connection.rollback()

    def cursor(self):
        return self.connection.cursor()

    @contextmanager
    def transaction(self):
        """Creates a transaction context for the connection."""
        try:
            yield self
            self.commit()
        except Exception:
            self.rollback()
            raise

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.rollback()
        else:
            self.commit()
        self.disconnect()
