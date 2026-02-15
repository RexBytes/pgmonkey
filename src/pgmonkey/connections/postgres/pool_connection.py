import logging
from contextlib import contextmanager, ExitStack
from psycopg_pool import ConnectionPool
from psycopg import OperationalError, conninfo as psycopg_conninfo
from .base_connection import PostgresBaseConnection

logger = logging.getLogger(__name__)


class PGPoolConnection(PostgresBaseConnection):
    def __init__(self, config, pool_settings=None):
        self.config = config
        self.pool_settings = pool_settings or {}
        self.pool = None
        self._conn = None

    @staticmethod
    def construct_conninfo(config):
        """Constructs a properly escaped connection info string from the config dictionary."""
        return psycopg_conninfo.make_conninfo(**config)

    def connect(self):
        """Initialize the connection pool."""
        if self.pool is None:
            kwargs = dict(self.pool_settings)
            check_on_checkout = kwargs.pop('check_on_checkout', False)
            if check_on_checkout:
                def _check(conn):
                    conn.execute("SELECT 1")
                kwargs['check'] = _check
            self.pool = ConnectionPool(
                conninfo=self.construct_conninfo(self.config),
                **kwargs,
            )

    def test_connection(self):
        """Tests both a single connection and pooling behavior from the pool."""
        try:
            with self.pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute('SELECT 1;')
                    result = cur.fetchone()
                    logger.info("Pool connection successful: %s", result)
        except OperationalError as e:
            logger.error("Single connection test failed: %s", e)
            return

        pool_min_size = self.pool_settings.get('min_size', 1)
        pool_max_size = self.pool_settings.get('max_size', 10)
        num_connections_to_test = min(pool_max_size, pool_min_size + 1)

        try:
            with ExitStack() as stack:
                connections = [
                    stack.enter_context(self.pool.connection())
                    for _ in range(num_connections_to_test)
                ]
                logger.info(
                    "Pooling test successful: Held %d connections concurrently "
                    "out of a possible %d",
                    len(connections), pool_max_size,
                )
        except OperationalError as e:
            logger.error("Pooling test failed: %s", e)

    def disconnect(self):
        """Closes all connections in the pool."""
        if self.pool:
            self.pool.close()
            self.pool = None

    def commit(self):
        if self._conn:
            self._conn.commit()

    def rollback(self):
        if self._conn:
            self._conn.rollback()

    def cursor(self):
        if self._conn:
            return self._conn.cursor()
        else:
            raise Exception("No active connection available from the pool")

    @contextmanager
    def transaction(self):
        """Creates a transaction context for the pooled connection."""
        with self.pool.connection() as conn:
            self._conn = conn
            try:
                yield self
                self.commit()
            except Exception:
                self.rollback()
                raise
            finally:
                self._conn = None

    def __enter__(self):
        """Acquire a connection from the pool."""
        if self.pool is None:
            self.connect()
        self._conn = self.pool.connection().__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type:
                self.rollback()
            else:
                self.commit()
        finally:
            if self._conn:
                self._conn.__exit__(exc_type, exc_val, exc_tb)
                self._conn = None
