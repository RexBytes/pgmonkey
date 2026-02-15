import pytest
import yaml
from unittest.mock import MagicMock
from pgmonkey.serversettings.postgres_server_config_generator import PostgresServerConfigGenerator


class TestHostToSubnet:

    def _make_generator(self, tmp_path, config):
        config_file = tmp_path / "config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config, f)
        return PostgresServerConfigGenerator(str(config_file))

    def test_ipv4_address_to_subnet(self, sample_config, tmp_path):
        gen = self._make_generator(tmp_path, sample_config)
        assert gen._host_to_subnet('192.168.1.100') == '192.168.1.0/24'

    def test_ipv4_zero_last_octet(self, sample_config, tmp_path):
        gen = self._make_generator(tmp_path, sample_config)
        assert gen._host_to_subnet('10.0.0.0') == '10.0.0.0/24'

    def test_hostname_returned_as_is(self, sample_config, tmp_path):
        gen = self._make_generator(tmp_path, sample_config)
        assert gen._host_to_subnet('localhost') == 'localhost'

    def test_fqdn_returned_as_is(self, sample_config, tmp_path):
        gen = self._make_generator(tmp_path, sample_config)
        assert gen._host_to_subnet('db.example.com') == 'db.example.com'


class TestPgHbaEntry:

    def _make_generator(self, tmp_path, config):
        config_file = tmp_path / "config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config, f)
        return PostgresServerConfigGenerator(str(config_file))

    def test_verify_full_generates_hostssl(self, sample_config, tmp_path):
        sample_config['postgresql']['connection_settings']['sslmode'] = 'verify-full'
        sample_config['postgresql']['connection_settings']['host'] = '192.168.1.50'
        gen = self._make_generator(tmp_path, sample_config)
        entries = gen.generate_pg_hba_entry()

        assert len(entries) == 2  # Header + entry
        assert 'hostssl' in entries[1]
        assert 'clientcert=verify-full' in entries[1]
        assert '192.168.1.0/24' in entries[1]

    def test_verify_ca_generates_hostssl(self, sample_config, tmp_path):
        sample_config['postgresql']['connection_settings']['sslmode'] = 'verify-ca'
        sample_config['postgresql']['connection_settings']['host'] = '10.0.0.5'
        gen = self._make_generator(tmp_path, sample_config)
        entries = gen.generate_pg_hba_entry()

        assert 'clientcert=verify-ca' in entries[1]

    def test_prefer_generates_host_reject(self, sample_config, tmp_path):
        sample_config['postgresql']['connection_settings']['sslmode'] = 'prefer'
        sample_config['postgresql']['connection_settings']['host'] = '192.168.1.50'
        gen = self._make_generator(tmp_path, sample_config)
        entries = gen.generate_pg_hba_entry()

        assert len(entries) == 2
        assert entries[1].startswith('host ')
        assert 'reject' in entries[1]

    def test_disable_generates_no_entry(self, sample_config, tmp_path):
        sample_config['postgresql']['connection_settings']['sslmode'] = 'disable'
        gen = self._make_generator(tmp_path, sample_config)
        entries = gen.generate_pg_hba_entry()

        assert len(entries) == 1  # Only header

    def test_localhost_host_handled(self, sample_config, tmp_path):
        sample_config['postgresql']['connection_settings']['host'] = 'localhost'
        sample_config['postgresql']['connection_settings']['sslmode'] = 'require'
        gen = self._make_generator(tmp_path, sample_config)
        entries = gen.generate_pg_hba_entry()

        assert 'localhost' in entries[1]


class TestPostgresqlConf:

    def _make_generator(self, tmp_path, config):
        config_file = tmp_path / "config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config, f)
        return PostgresServerConfigGenerator(str(config_file))

    def test_pool_max_connections(self, sample_config, tmp_path):
        """max_connections should be 1.1x the larger of pool_settings or async_pool_settings max_size."""
        sample_config['postgresql']['pool_settings']['max_size'] = 20
        sample_config['postgresql']['async_pool_settings']['max_size'] = 10
        gen = self._make_generator(tmp_path, sample_config)
        settings = gen.generate_postgresql_conf()

        assert 'max_connections = 22' in settings  # int(20 * 1.1)

    def test_async_pool_larger_max_connections(self, sample_config, tmp_path):
        sample_config['postgresql']['pool_settings']['max_size'] = 5
        sample_config['postgresql']['async_pool_settings']['max_size'] = 50
        gen = self._make_generator(tmp_path, sample_config)
        settings = gen.generate_postgresql_conf()

        assert 'max_connections = 55' in settings  # int(50 * 1.1)

    def test_string_max_size_handled(self, sample_config, tmp_path):
        """max_size as a quoted string in YAML should not crash."""
        sample_config['postgresql']['pool_settings']['max_size'] = '20'
        sample_config['postgresql']['async_pool_settings']['max_size'] = '10'
        gen = self._make_generator(tmp_path, sample_config)
        settings = gen.generate_postgresql_conf()

        assert 'max_connections = 22' in settings  # int(20 * 1.1)

    def test_no_pool_settings_defaults_to_20(self, sample_config, tmp_path):
        del sample_config['postgresql']['pool_settings']
        del sample_config['postgresql']['async_pool_settings']
        gen = self._make_generator(tmp_path, sample_config)
        settings = gen.generate_postgresql_conf()

        assert 'max_connections = 20' in settings

    def test_ssl_enabled_generates_ssl_settings(self, sample_config, tmp_path):
        sample_config['postgresql']['connection_settings']['sslmode'] = 'require'
        gen = self._make_generator(tmp_path, sample_config)
        settings = gen.generate_postgresql_conf()

        assert 'ssl = on' in settings
        assert "ssl_cert_file = 'server.crt'" in settings

    def test_ssl_disabled_no_ssl_settings(self, sample_config, tmp_path):
        sample_config['postgresql']['connection_settings']['sslmode'] = 'disable'
        gen = self._make_generator(tmp_path, sample_config)
        settings = gen.generate_postgresql_conf()

        assert 'ssl = on' not in settings


class TestPrintConfigurations:

    def _make_generator(self, tmp_path, config):
        config_file = tmp_path / "config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config, f)
        return PostgresServerConfigGenerator(str(config_file))

    def test_print_configurations_outputs_text(self, sample_config, tmp_path, capsys):
        gen = self._make_generator(tmp_path, sample_config)
        gen.print_configurations()
        output = capsys.readouterr().out
        assert 'PostgreSQL' in output
        assert 'postgresql.conf' in output

    def test_file_not_found_prints_error(self, capsys):
        gen = PostgresServerConfigGenerator('/nonexistent/path.yaml')
        assert gen.config is None
        output = capsys.readouterr().out
        assert 'Error: File not found' in output


class TestPrintConfigurationsWithAudit:

    def _make_generator(self, tmp_path, config):
        config_file = tmp_path / "config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config, f)
        return PostgresServerConfigGenerator(str(config_file))

    def _make_mock_connection(self, pg_settings_rows, hba_rows=None, hba_error=None):
        """Create a mock connection that returns different results per query."""
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        call_count = [0]

        def side_effect_execute(query, params=None):
            call_count[0] += 1
            if 'pg_settings' in query:
                cursor.fetchall.return_value = pg_settings_rows
            elif 'pg_hba_file_rules' in query:
                if hba_error:
                    raise hba_error
                cursor.description = [
                    ('line_number',), ('type',), ('database',), ('user_name',),
                    ('address',), ('netmask',), ('auth_method',), ('options',),
                ]
                cursor.fetchall.return_value = hba_rows or []

        cursor.execute.side_effect = side_effect_execute
        return conn

    def test_audit_shows_comparison_table(self, sample_config, tmp_path, capsys):
        sample_config['postgresql']['connection_settings']['sslmode'] = 'require'
        gen = self._make_generator(tmp_path, sample_config)

        conn = self._make_mock_connection(
            pg_settings_rows=[
                ('max_connections', '100', 'configuration file'),
                ('ssl', 'on', 'configuration file'),
                ('ssl_cert_file', 'server.crt', 'configuration file'),
                ('ssl_key_file', 'server.key', 'configuration file'),
                ('ssl_ca_file', 'ca.crt', 'configuration file'),
            ],
            hba_error=Exception('relation "pg_hba_file_rules" does not exist'),
        )
        gen.print_configurations_with_audit(conn)
        output = capsys.readouterr().out

        assert 'Server settings audit' in output
        assert 'postgresql.conf' in output
        assert 'Setting' in output
        assert 'Recommended' in output
        assert 'Current' in output
        assert 'OK' in output

    def test_audit_shows_mismatch(self, sample_config, tmp_path, capsys):
        sample_config['postgresql']['connection_settings']['sslmode'] = 'require'
        gen = self._make_generator(tmp_path, sample_config)

        conn = self._make_mock_connection(
            pg_settings_rows=[
                ('max_connections', '5', 'default'),
                ('ssl', 'off', 'default'),
            ],
            hba_error=Exception('relation "pg_hba_file_rules" does not exist'),
        )
        gen.print_configurations_with_audit(conn)
        output = capsys.readouterr().out

        assert 'MISMATCH' in output

    def test_audit_falls_back_on_permission_denied(self, sample_config, tmp_path, capsys):
        gen = self._make_generator(tmp_path, sample_config)

        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        cursor.execute.side_effect = Exception("permission denied for view pg_settings")

        gen.print_configurations_with_audit(conn)
        output = capsys.readouterr().out

        assert 'permission denied' in output.lower()
        assert 'Showing recommendations only' in output

    def test_audit_with_no_config_prints_error(self, capsys):
        gen = PostgresServerConfigGenerator('/nonexistent/path.yaml')
        capsys.readouterr()  # clear file-not-found output
        conn = MagicMock()
        gen.print_configurations_with_audit(conn)
        output = capsys.readouterr().out

        assert 'Configuration data is not available' in output

    def test_audit_shows_hba_rules(self, sample_config, tmp_path, capsys):
        sample_config['postgresql']['connection_settings']['sslmode'] = 'require'
        gen = self._make_generator(tmp_path, sample_config)

        conn = self._make_mock_connection(
            pg_settings_rows=[
                ('max_connections', '100', 'configuration file'),
                ('ssl', 'on', 'configuration file'),
            ],
            hba_rows=[
                (1, 'local', ['all'], ['all'], None, None, 'peer', None),
                (2, 'host', ['all'], ['all'], '127.0.0.1/32', None, 'md5', None),
            ],
        )
        gen.print_configurations_with_audit(conn)
        output = capsys.readouterr().out

        assert 'Current server rules' in output
        assert 'local' in output
        assert 'Recommended entries' in output
