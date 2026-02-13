import pytest
import yaml
import tempfile
import os


def pytest_collection_modifyitems(config, items):
    """Skip async tests gracefully when pytest-asyncio is not installed."""
    try:
        import pytest_asyncio  # noqa: F401
    except ImportError:
        skip_async = pytest.mark.skip(reason="pytest-asyncio is not installed")
        for item in items:
            if "asyncio" in item.keywords:
                item.add_marker(skip_async)


@pytest.fixture
def sample_config():
    """Returns a full pgmonkey configuration dictionary for testing."""
    return {
        'postgresql': {
            'connection_type': 'normal',
            'connection_settings': {
                'user': 'testuser',
                'password': 'testpass',
                'host': 'localhost',
                'port': '5432',
                'dbname': 'testdb',
                'sslmode': 'prefer',
                'sslcert': '',
                'sslkey': '',
                'sslrootcert': '',
                'connect_timeout': '10',
                'application_name': 'pgmonkey_test',
                'keepalives': '1',
                'keepalives_idle': '60',
                'keepalives_interval': '15',
                'keepalives_count': '5',
            },
            'pool_settings': {
                'min_size': 2,
                'max_size': 10,
                'max_idle': 300,
                'max_lifetime': 3600,
            },
            'async_settings': {
                'idle_in_transaction_session_timeout': '5000',
                'statement_timeout': '30000',
                'lock_timeout': '10000',
            },
            'async_pool_settings': {
                'min_size': 2,
                'max_size': 10,
                'max_idle': 300,
                'max_lifetime': 3600,
            },
        }
    }


@pytest.fixture
def sample_config_file(sample_config, tmp_path):
    """Writes the sample config to a temp YAML file and returns the path."""
    config_file = tmp_path / "test_config.yaml"
    with open(config_file, 'w') as f:
        yaml.dump(sample_config, f, sort_keys=False)
    return str(config_file)


@pytest.fixture
def filtered_connection_settings():
    """Returns the expected filtered connection settings (empty values stripped)."""
    return {
        'user': 'testuser',
        'password': 'testpass',
        'host': 'localhost',
        'port': '5432',
        'dbname': 'testdb',
        'sslmode': 'prefer',
        'connect_timeout': '10',
        'application_name': 'pgmonkey_test',
        'keepalives': '1',
        'keepalives_idle': '60',
        'keepalives_interval': '15',
        'keepalives_count': '5',
    }


@pytest.fixture
def ssl_config(sample_config):
    """Returns config with verify-full SSL mode and cert paths set."""
    config = sample_config.copy()
    config['postgresql']['connection_settings']['sslmode'] = 'verify-full'
    config['postgresql']['connection_settings']['sslcert'] = '/path/to/client.crt'
    config['postgresql']['connection_settings']['sslkey'] = '/path/to/client.key'
    config['postgresql']['connection_settings']['sslrootcert'] = '/path/to/ca.crt'
    return config


@pytest.fixture
def ssl_config_file(ssl_config, tmp_path):
    """Writes the SSL config to a temp YAML file and returns the path."""
    config_file = tmp_path / "test_ssl_config.yaml"
    with open(config_file, 'w') as f:
        yaml.dump(ssl_config, f, sort_keys=False)
    return str(config_file)
