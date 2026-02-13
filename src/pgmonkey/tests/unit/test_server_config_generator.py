import pytest
import yaml
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
