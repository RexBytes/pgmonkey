from contextlib import contextmanager
from psycopg_pool import ConnectionPool
from psycopg import OperationalError
# Assuming PostgresBaseConnection is correctly implemented elsewhere
from .base_connection import PostgresBaseConnection


class PGPoolConnection(PostgresBaseConnection):
    def __init__(self, config, pool_settings=None):
        super().__init__()  # Initialize the base class, if necessary
        self.config = config
        self.pool_settings = pool_settings or {}
        # Directly pass connection parameters and pool settings to ConnectionPool
        self.pool = ConnectionPool(conninfo=self.construct_conninfo(self.config), **self.pool_settings)
        self._conn = None

    @staticmethod
    def construct_conninfo(config):
        """Constructs a connection info string from the config dictionary, excluding pool settings."""
        # Filter out 'pool_settings' and any other non-connection parameters
        conn_params = {k: v for k, v in config.items() if k not in ['pool_settings'] and v is not None}
        # Construct and return the connection info string
        return " ".join([f"{k}={v}" for k, v in conn_params.items()])

    def test_connection(self):
        """Tests both a single connection and pooling behavior from the pool."""
        try:
            with self.pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute('SELECT 1;')
                    result = cur.fetchone()
                    print("Pool connection successful: ", result)
        except OperationalError as e:
            print(f"Single connection test failed: {e}")
            return

        # Test pooling behavior
        pool_min_size = self.pool_settings.get('min_size', 1)
        pool_max_size = self.pool_settings.get('max_size', 10)
        num_connections_to_test = min(pool_max_size, pool_min_size + 1)

        connections = []
        try:
            for _ in range(num_connections_to_test):
                with self.pool.connection() as conn:
                    connections.append(conn)

            print(f"Pooling test successful: Acquired {len(connections)} connections out of a possible {pool_max_size}")
        except OperationalError as e:
            print(f"Pooling test failed: {e}")

        if len(connections) == num_connections_to_test:
            print(f"Async pooling tested successfully with {len(connections)} concurrent connections.")
        else:
            print(f"Async pooling test did not pass, only {len(connections)} connections acquired.")

    def disconnect(self):
        """Closes all connections in the pool."""
        if self.pool:
            self.pool.close()
            self.pool = None

    def connect(self):
        # The connection pool is initialized in the constructor, so no action is needed here.
        pass

    def commit(self):
        """Commits the current transaction on the pooled connection."""
        if self._conn:
            self._conn.commit()

    def rollback(self):
        """Rolls back the current transaction on the pooled connection."""
        if self._conn:
            self._conn.rollback()

    def cursor(self):
        """Returns a cursor object from the current pooled connection."""
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
                yield self  # Let the caller use the connection within the transaction
                self.commit()  # Commit if everything is successful
            except Exception:
                self.rollback()  # Rollback if there is any exception
                raise  # Re-raise the exception to propagate it
            finally:
                self._conn = None  # Clear the connection after the transaction is done

    def __enter__(self):
        """Acquire a connection from the pool."""
        self._conn = self.pool.connection().__enter__()  # Get a connection from the pool
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Handles transaction commit/rollback and closes the acquired connection."""
        try:
            if exc_type:
                self.rollback()
            else:
                self.commit()
        finally:
            if self._conn:
                self._conn.__exit__(exc_type, exc_val, exc_tb)  # Properly handle psycopg connection teardown
                self._conn = None
