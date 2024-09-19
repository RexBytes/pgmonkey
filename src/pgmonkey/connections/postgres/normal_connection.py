from psycopg import connect, OperationalError  # This imports psycopg3, assuming you have installed 'psycopg' version 3+
from .base_connection import PostgresBaseConnection


class PGNormalConnection(PostgresBaseConnection):
    def __init__(self, config):
        # The configuration dict should contain connection parameters like dbname, user, password, etc.
        self.config = config
        self.connection = None

    def connect(self):
        # Establishes a synchronous connection to the PostgreSQL server.
        # The 'connect' function is used both in psycopg2 and psycopg3 for this purpose.
        self.connection = connect(**self.config)


    def test_connection(self):
        """Tests a synchronous (normal) database connection."""
        try:
            with self.connection.cursor() as cur:
                cur.execute('SELECT 1;')  # Execute a simple query to test the connection.
                result = cur.fetchone()
                print("Connection successful: ", result)

        except OperationalError as e:
            print(f"Connection failed: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
        finally:
            # Optionally close the connection if it should only be used for this test
            if self.connection and not self.connection.closed:
                self.connection.close()
                print("Connection closed.")

    def disconnect(self):
        # Closes the connection to the database.
        if self.connection:
            self.connection.close()

    def __enter__(self):
        # Ensures the connection is established when entering the context.
        if not self.connection:
            self.connect()
        return self.connection

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Closes the connection when exiting the context.
        self.disconnect()
