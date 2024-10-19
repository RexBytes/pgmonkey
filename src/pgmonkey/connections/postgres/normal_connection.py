from psycopg import connect, OperationalError
from .base_connection import PostgresBaseConnection
from contextlib import contextmanager

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
                print("Connection successful: ", result)
        except OperationalError as e:
            print(f"Connection failed: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

    def disconnect(self):
        """Closes the database connection."""
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
            yield self  # Let the caller use the connection within the transaction
            self.commit()  # Commit if everything is successful
        except Exception:
            self.rollback()  # Rollback if there is any exception
            raise  # Re-raise the exception to propagate it
        finally:
            self.disconnect()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.rollback()
        else:
            self.commit()
        self.disconnect()


