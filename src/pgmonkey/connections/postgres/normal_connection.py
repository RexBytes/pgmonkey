import logging
from psycopg import connect, OperationalError, sql
from .base_connection import PostgresBaseConnection
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class PGNormalConnection(PostgresBaseConnection):
    def __init__(self, config, sync_settings=None):
        self.config = config
        self.sync_settings = sync_settings or {}
        self.autocommit = None
        self.connection = None

    def connect(self):
        if self.connection is None or self.connection.closed:
            self.connection = connect(autocommit=bool(self.autocommit), **self.config)
            self._apply_sync_settings()

    def _apply_sync_settings(self):
        """Applies PostgreSQL GUC settings via SET commands after connection is established."""
        for setting, value in self.sync_settings.items():
            try:
                self.connection.execute(sql.SQL("SET {} = %s").format(sql.Identifier(setting)), (str(value),))
            except Exception as e:
                logger.warning("Could not apply setting '%s': %s", setting, e)

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
        try:
            if exc_type:
                self.rollback()
            else:
                self.commit()
        finally:
            self.disconnect()
