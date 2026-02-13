import pytest
from pgmonkey.connections.postgres.base_connection import PostgresBaseConnection


class TestPostgresBaseConnection:

    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            PostgresBaseConnection()

    def test_subclass_missing_methods_raises(self):
        class IncompleteConnection(PostgresBaseConnection):
            def connect(self): pass

        with pytest.raises(TypeError):
            IncompleteConnection()

    def test_complete_subclass_can_instantiate(self):
        class CompleteConnection(PostgresBaseConnection):
            def connect(self): pass
            def test_connection(self): pass
            def disconnect(self): pass
            def commit(self): pass
            def rollback(self): pass
            def cursor(self): pass

        conn = CompleteConnection()
        assert conn is not None
