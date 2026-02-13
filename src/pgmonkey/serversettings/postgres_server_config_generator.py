import ipaddress
import yaml


class PostgresServerConfigGenerator:
    def __init__(self, yaml_file_path):
        self.yaml_file_path = yaml_file_path
        self.config = self._read_yaml()

    def _read_yaml(self):
        """Reads the YAML configuration file."""
        try:
            with open(self.yaml_file_path, 'r') as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            print(f"Error: File not found - {self.yaml_file_path}")
        except yaml.YAMLError as e:
            print(f"Error reading YAML file: {e}")
        except Exception as e:
            print(f"An error occurred: {e}")

    def _host_to_subnet(self, host):
        """Converts a host to a /24 subnet string. Returns the host as-is if not a valid IPv4 address."""
        try:
            addr = ipaddress.ip_address(host)
            network = ipaddress.ip_network(f"{addr}/24", strict=False)
            return str(network)
        except ValueError:
            # Not an IP address (e.g. hostname like 'localhost') - return as-is
            return host

    def generate_pg_hba_entry(self):
        """Generates entries for pg_hba.conf based on the SSL settings."""
        host = self.config['postgresql']['connection_settings']['host']
        sslmode = self.config['postgresql']['connection_settings'].get('sslmode', 'prefer')
        entries = []
        header = "TYPE  DATABASE  USER  ADDRESS          METHOD  OPTIONS"
        entries.append(header)

        address = self._host_to_subnet(host)

        if sslmode in ['verify-ca', 'verify-full']:
            clientcert = 'verify-full' if sslmode == 'verify-full' else 'verify-ca'
            entry = f"hostssl all     all   {address}    md5     clientcert={clientcert}"
            entries.append(entry)
        elif sslmode != 'disable':
            entry = f"host    all     all   {address}    reject"
            entries.append(entry)
        return entries

    def generate_postgresql_conf(self):
        """Generates minimal entries for postgresql.conf based on connection settings."""
        settings = []
        pg_config = self.config['postgresql']

        # Check both pool_settings and async_pool_settings for max_size
        pool_settings = pg_config.get('pool_settings', {})
        async_pool_settings = pg_config.get('async_pool_settings', {})

        # Use the larger max_size from either pool type
        pool_max = pool_settings.get('max_size', 0) if pool_settings else 0
        async_pool_max = async_pool_settings.get('max_size', 0) if async_pool_settings else 0
        max_size = max(pool_max, async_pool_max)

        if max_size > 0:
            max_connections = int(max_size * 1.1)
            settings.append(f"max_connections = {max_connections}")
        else:
            settings.append("max_connections = 20")

        settings.extend(self._generate_ssl_settings())
        return settings

    def _generate_ssl_settings(self):
        """Generates SSL configuration entries for postgresql.conf based on client settings."""
        ssl_settings = []
        sslmode = self.config['postgresql']['connection_settings'].get('sslmode', 'disable')
        if sslmode != 'disable':
            ssl_settings.append("ssl = on")
            ssl_settings.append("ssl_cert_file = 'server.crt'")
            ssl_settings.append("ssl_key_file = 'server.key'")
            ssl_settings.append("ssl_ca_file = 'ca.crt'")
        return ssl_settings

    def print_configurations(self):
        """Prints the generated server configurations."""
        if not self.config:
            print("Configuration data is not available. Please check the file path and contents.")
            return

        pg_hba_entries = self.generate_pg_hba_entry()
        postgresql_conf_entries = self.generate_postgresql_conf()
        print("1) Database type detected: PostgreSQL\n")
        print("2) Minimal database server settings needed for this config file:\n")

        if len(pg_hba_entries) > 1:
            print("   a) pg_hba.conf:\n")
            print('\n'.join(pg_hba_entries) + "\n")
        else:
            print("   a) No entries needed for pg_hba.conf.\n")

        if postgresql_conf_entries:
            print("   b) postgresql.conf:\n")
            print('\n'.join(postgresql_conf_entries))
        else:
            print("   b) No entries needed for postgresql.conf.\n")

        print()

        files_to_check = []
        if len(pg_hba_entries) > 1:
            files_to_check.append("pg_hba.conf")
        if postgresql_conf_entries:
            files_to_check.append("postgresql.conf")

        if files_to_check:
            print(f"Please check the following files on your system and ensure that the appropriate settings are applied: {', '.join(files_to_check)}.")
            print("Ensure that the network ADDRESS matches your network subnet and review all configurations.")
