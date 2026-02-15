import logging
import threading
from contextlib import contextmanager, ExitStack
from psycopg_pool import ConnectionPool
from psycopg import OperationalError, conninfo as psycopg_conninfo, sql
from .base_connection import PostgresBaseConnection

logger = logging.getLogger(__name__)


class PGPoolConnection(PostgresBaseConnection):
    def __init__(self, config, pool_settings=None, sync_settings=None):
        self.config = config
        self.pool_settings = pool_settings or {}
        self.sync_settings = sync_settings or {}
        self.pool = None
        self._local = threading.local()

    @staticmethod
    def construct_conninfo(config):
        """Constructs a properly escaped connection info string from the config dictionary."""
        return psycopg_conninfo.make_conninfo(**config)

    def _get_conn(self):
        """Get the thread-local borrowed connection."""
        return getattr(self._local, 'conn', None)

    def _set_conn(self, value):
        """Set the thread-local borrowed connection."""
        self._local.conn = value

    def connect(self):
        """Initialize the connection pool."""
        if self.pool is None:
            conninfo = self.construct_conninfo(self.config)
            kwargs = dict(self.pool_settings)

            check_on_checkout = kwargs.pop('check_on_checkout', False)
            if check_on_checkout:
                def _check(conn):
                    conn.execute("SELECT 1")
                kwargs['check'] = _check

            if self.sync_settings:
                sync_settings = self.sync_settings

                def _configure(conn):
                    for setting, value in sync_settings.items():
                        try:
                            conn.execute(sql.SQL("SET {} = %s").format(sql.Identifier(setting)), (str(value),))
                        except Exception as e:
                            logger.warning("Could not apply setting '%s': %s", setting, e)
                kwargs['configure'] = _configure

            self.pool = ConnectionPool(conninfo=conninfo, **kwargs)

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
        conn = self._get_conn()
        if conn:
            conn.commit()

    def rollback(self):
        conn = self._get_conn()
        if conn:
            conn.rollback()

    def cursor(self):
        conn = self._get_conn()
        if conn:
            return conn.cursor()
        else:
            raise Exception("No active connection available from the pool")

    @contextmanager
    def transaction(self):
        """Creates a transaction context for the pooled connection."""
        conn = self._get_conn()
        if conn:
            # Inside __enter__/__exit__ context - use the acquired connection
            with conn.transaction():
                yield self
        elif self.pool:
            # Standalone usage - acquire connection from pool
            with self.pool.connection() as acquired:
                self._set_conn(acquired)
                try:
                    with acquired.transaction():
                        yield self
                finally:
                    self._set_conn(None)
        else:
            raise Exception("No active pool available for transaction")

    def __enter__(self):
        """Acquire a connection from the pool."""
        if self.pool is None:
            self.connect()
        pool_conn_ctx = self.pool.connection()
        self._local.pool_conn_ctx = pool_conn_ctx
        self._set_conn(pool_conn_ctx.__enter__())
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type:
                self.rollback()
            else:
                self.commit()
        finally:
            conn = self._get_conn()
            pool_conn_ctx = getattr(self._local, 'pool_conn_ctx', None)
            if conn and pool_conn_ctx:
                pool_conn_ctx.__exit__(exc_type, exc_val, exc_tb)
            self._set_conn(None)
            self._local.pool_conn_ctx = None
