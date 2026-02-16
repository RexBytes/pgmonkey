import pytest
from unittest.mock import MagicMock, patch
from pgmonkey.serversettings.postgres_server_settings_inspector import (
    PostgresServerSettingsInspector,
    POSTGRESQL_CONF_SETTINGS,
)


@pytest.fixture
def mock_connection():
    """Returns a mock connection with a working cursor context manager."""
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return conn, cursor


class TestGetCurrentSettings:

    def test_returns_settings_dict(self, mock_connection):
        conn, cursor = mock_connection
        cursor.fetchall.return_value = [
            ('max_connections', '100', 'configuration file'),
            ('ssl', 'on', 'configuration file'),
        ]
        inspector = PostgresServerSettingsInspector(conn)
        result = inspector.get_current_settings()

        assert result is not None
        assert result['max_connections'] == {'value': '100', 'source': 'configuration file'}
        assert result['ssl'] == {'value': 'on', 'source': 'configuration file'}

    def test_queries_correct_settings(self, mock_connection):
        conn, cursor = mock_connection
        cursor.fetchall.return_value = []
        inspector = PostgresServerSettingsInspector(conn)
        inspector.get_current_settings()

        cursor.execute.assert_called_once()
        call_args = cursor.execute.call_args
        assert 'pg_settings' in call_args[0][0]
        assert call_args[0][1] == (POSTGRESQL_CONF_SETTINGS,)

    def test_permission_denied_returns_none(self, mock_connection, capsys):
        conn, cursor = mock_connection
        cursor.execute.side_effect = Exception("permission denied for view pg_settings")
        inspector = PostgresServerSettingsInspector(conn)
        result = inspector.get_current_settings()

        assert result is None
        output = capsys.readouterr().out
        assert 'permission denied' in output.lower()

    def test_insufficient_privilege_returns_none(self, mock_connection, capsys):
        conn, cursor = mock_connection
        cursor.execute.side_effect = Exception("ERROR: insufficient privilege")
        inspector = PostgresServerSettingsInspector(conn)
        result = inspector.get_current_settings()

        assert result is None
        output = capsys.readouterr().out
        assert 'permission denied' in output.lower()

    def test_generic_error_returns_none(self, mock_connection, capsys):
        conn, cursor = mock_connection
        cursor.execute.side_effect = Exception("connection reset by peer")
        inspector = PostgresServerSettingsInspector(conn)
        result = inspector.get_current_settings()

        assert result is None
        output = capsys.readouterr().out
        assert 'Could not query server settings' in output

    def test_empty_result_returns_empty_dict(self, mock_connection):
        conn, cursor = mock_connection
        cursor.fetchall.return_value = []
        inspector = PostgresServerSettingsInspector(conn)
        result = inspector.get_current_settings()

        assert result == {}


class TestGetHbaRules:

    def test_returns_list_of_dicts(self, mock_connection):
        conn, cursor = mock_connection
        cursor.description = [
            ('line_number',), ('type',), ('database',), ('user_name',),
            ('address',), ('netmask',), ('auth_method',), ('options',),
        ]
        cursor.fetchall.return_value = [
            (1, 'local', ['all'], ['all'], None, None, 'peer', None),
            (2, 'hostssl', ['all'], ['all'], '192.168.1.0/24', None, 'md5', ['clientcert=verify-full']),
        ]
        inspector = PostgresServerSettingsInspector(conn)
        result = inspector.get_hba_rules()

        assert result is not None
        assert len(result) == 2
        assert result[0]['type'] == 'local'
        assert result[1]['auth_method'] == 'md5'

    def test_permission_denied_returns_none(self, mock_connection):
        conn, cursor = mock_connection
        cursor.execute.side_effect = Exception("permission denied for view pg_hba_file_rules")
        inspector = PostgresServerSettingsInspector(conn)
        result = inspector.get_hba_rules()

        assert result is None

    def test_view_not_found_returns_none(self, mock_connection):
        conn, cursor = mock_connection
        cursor.execute.side_effect = Exception('relation "pg_hba_file_rules" does not exist')
        inspector = PostgresServerSettingsInspector(conn)
        result = inspector.get_hba_rules()

        assert result is None

    def test_generic_error_returns_none(self, mock_connection):
        conn, cursor = mock_connection
        cursor.execute.side_effect = Exception("something went wrong")
        inspector = PostgresServerSettingsInspector(conn)
        result = inspector.get_hba_rules()

        assert result is None


class TestCompareSettings:

    def test_matching_settings(self, mock_connection):
        conn, cursor = mock_connection
        cursor.fetchall.return_value = [
            ('ssl', 'on', 'configuration file'),
            ('ssl_cert_file', 'server.crt', 'configuration file'),
        ]
        inspector = PostgresServerSettingsInspector(conn)
        result = inspector.compare_settings([
            "ssl = on",
            "ssl_cert_file = 'server.crt'",
        ])

        assert result is not None
        assert len(result) == 2
        assert result[0]['status'] == 'OK'
        assert result[1]['status'] == 'OK'

    def test_mismatched_ssl(self, mock_connection):
        conn, cursor = mock_connection
        cursor.fetchall.return_value = [
            ('ssl', 'off', 'default'),
        ]
        inspector = PostgresServerSettingsInspector(conn)
        result = inspector.compare_settings(["ssl = on"])

        assert result[0]['status'] == 'MISMATCH'
        assert result[0]['current'] == 'off'
        assert result[0]['recommended'] == 'on'

    def test_max_connections_sufficient(self, mock_connection):
        conn, cursor = mock_connection
        cursor.fetchall.return_value = [
            ('max_connections', '200', 'configuration file'),
        ]
        inspector = PostgresServerSettingsInspector(conn)
        result = inspector.compare_settings(["max_connections = 22"])

        assert result[0]['status'] == 'OK'

    def test_max_connections_insufficient(self, mock_connection):
        conn, cursor = mock_connection
        cursor.fetchall.return_value = [
            ('max_connections', '10', 'default'),
        ]
        inspector = PostgresServerSettingsInspector(conn)
        result = inspector.compare_settings(["max_connections = 22"])

        assert result[0]['status'] == 'MISMATCH'

    def test_missing_setting_returns_unknown(self, mock_connection):
        conn, cursor = mock_connection
        cursor.fetchall.return_value = []
        inspector = PostgresServerSettingsInspector(conn)
        result = inspector.compare_settings(["ssl = on"])

        assert result[0]['status'] == 'UNKNOWN'
        assert result[0]['current'] == '(not found)'

    def test_permission_denied_returns_none(self, mock_connection, capsys):
        conn, cursor = mock_connection
        cursor.execute.side_effect = Exception("permission denied")
        inspector = PostgresServerSettingsInspector(conn)
        result = inspector.compare_settings(["ssl = on"])

        assert result is None

    def test_file_path_review(self, mock_connection):
        conn, cursor = mock_connection
        cursor.fetchall.return_value = [
            ('ssl_ca_file', 'root.crt', 'configuration file'),
        ]
        inspector = PostgresServerSettingsInspector(conn)
        result = inspector.compare_settings(["ssl_ca_file = 'ca.crt'"])

        assert result[0]['status'] == 'REVIEW'
        assert result[0]['current'] == 'root.crt'
        assert result[0]['recommended'] == 'ca.crt'


class TestEvaluateStatus:

    def test_max_connections_equal(self):
        assert PostgresServerSettingsInspector._evaluate_status('max_connections', '22', '22') == 'OK'

    def test_max_connections_greater(self):
        assert PostgresServerSettingsInspector._evaluate_status('max_connections', '22', '100') == 'OK'

    def test_max_connections_less(self):
        assert PostgresServerSettingsInspector._evaluate_status('max_connections', '22', '10') == 'MISMATCH'

    def test_max_connections_non_numeric(self):
        assert PostgresServerSettingsInspector._evaluate_status('max_connections', '22', 'abc') == 'UNKNOWN'

    def test_ssl_match(self):
        assert PostgresServerSettingsInspector._evaluate_status('ssl', 'on', 'on') == 'OK'

    def test_ssl_mismatch(self):
        assert PostgresServerSettingsInspector._evaluate_status('ssl', 'on', 'off') == 'MISMATCH'

    def test_ssl_case_insensitive(self):
        assert PostgresServerSettingsInspector._evaluate_status('ssl', 'ON', 'on') == 'OK'

    def test_file_path_match(self):
        assert PostgresServerSettingsInspector._evaluate_status('ssl_cert_file', 'server.crt', 'server.crt') == 'OK'

    def test_file_path_mismatch(self):
        assert PostgresServerSettingsInspector._evaluate_status('ssl_cert_file', 'server.crt', 'other.crt') == 'REVIEW'

    def test_null_current_returns_unknown(self):
        """pg_settings can return NULL values - should not crash."""
        assert PostgresServerSettingsInspector._evaluate_status('ssl', 'on', None) == 'UNKNOWN'
        assert PostgresServerSettingsInspector._evaluate_status('max_connections', '22', None) == 'UNKNOWN'
        assert PostgresServerSettingsInspector._evaluate_status('ssl_cert_file', 'server.crt', None) == 'UNKNOWN'
