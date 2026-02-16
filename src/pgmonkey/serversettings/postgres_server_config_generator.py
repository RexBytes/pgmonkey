import ipaddress
import yaml
from pgmonkey.serversettings.postgres_server_settings_inspector import PostgresServerSettingsInspector
from pgmonkey.common.utils.configutils import normalize_config


class PostgresServerConfigGenerator:
    def __init__(self, yaml_file_path):
        self.yaml_file_path = yaml_file_path
        self.config = self._read_yaml()

    def _read_yaml(self):
        """Reads the YAML configuration file."""
        try:
            with open(self.yaml_file_path, 'r') as file:
                data = yaml.safe_load(file)
            return normalize_config(data)
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
        host = self.config['connection_settings']['host']
        sslmode = self.config['connection_settings'].get('sslmode', 'prefer')
        entries = []
        header = "TYPE  DATABASE  USER  ADDRESS          METHOD  OPTIONS"
        entries.append(header)

        address = self._host_to_subnet(host)

        if sslmode in ['verify-ca', 'verify-full']:
            clientcert = 'verify-full' if sslmode == 'verify-full' else 'verify-ca'
            entry = f"hostssl all     all   {address}    md5     clientcert={clientcert}"
            entries.append(entry)
        elif sslmode != 'disable':
            entry = f"hostssl all     all   {address}    md5"
            entries.append(entry)
        return entries

    def generate_postgresql_conf(self):
        """Generates minimal entries for postgresql.conf based on connection settings."""
        settings = []
        pg_config = self.config

        # Check both pool_settings and async_pool_settings for max_size
        pool_settings = pg_config.get('pool_settings', {})
        async_pool_settings = pg_config.get('async_pool_settings', {})

        # Use the larger max_size from either pool type
        pool_max = int(pool_settings.get('max_size', 0)) if pool_settings else 0
        async_pool_max = int(async_pool_settings.get('max_size', 0)) if async_pool_settings else 0
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
        sslmode = self.config['connection_settings'].get('sslmode', 'disable')
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

    def print_configurations_with_audit(self, connection):
        """Prints recommended settings compared against live server values.

        Falls back to print_configurations() if the live query fails.
        """
        if not self.config:
            print("Configuration data is not available. Please check the file path and contents.")
            return

        inspector = PostgresServerSettingsInspector(connection)
        postgresql_conf_entries = self.generate_postgresql_conf()
        pg_hba_entries = self.generate_pg_hba_entry()

        print("1) Database type detected: PostgreSQL\n")
        print("2) Server settings audit:\n")

        # postgresql.conf comparison
        comparisons = inspector.compare_settings(postgresql_conf_entries)
        if comparisons is not None:
            self._print_comparison_table(comparisons)
        else:
            print("   Showing recommendations only.\n")
            if postgresql_conf_entries:
                print("   postgresql.conf:\n")
                print('\n'.join(f"   {entry}" for entry in postgresql_conf_entries))
            print()

        # pg_hba.conf inspection
        print()
        hba_rules = inspector.get_hba_rules()
        if hba_rules is not None:
            self._print_hba_audit(pg_hba_entries, hba_rules)
        else:
            print("   pg_hba.conf:")
            print("   (pg_hba_file_rules not available or insufficient privileges"
                  " - showing recommendations only)\n")
            if len(pg_hba_entries) > 1:
                print("   Recommended pg_hba.conf entries:\n")
                print('\n'.join(f"   {entry}" for entry in pg_hba_entries))
            else:
                print("   No entries needed for pg_hba.conf.")
            print()

    @staticmethod
    def _print_comparison_table(comparisons):
        """Prints a formatted comparison table of recommended vs current settings."""
        setting_w = max(len('Setting'), max((len(c['setting']) for c in comparisons), default=0))
        rec_w = max(len('Recommended'), max((len(c['recommended']) for c in comparisons), default=0))
        cur_w = max(len('Current'), max((len(c['current']) for c in comparisons), default=0))
        src_w = max(len('Source'), max((len(c['source']) for c in comparisons), default=0))
        status_w = max(len('Status'), max((len(c['status']) for c in comparisons), default=0))

        header = (f"   {'Setting':<{setting_w}}  {'Recommended':<{rec_w}}  "
                  f"{'Current':<{cur_w}}  {'Source':<{src_w}}  {'Status':<{status_w}}")
        separator = f"   {'─' * (setting_w + rec_w + cur_w + src_w + status_w + 8)}"

        print("   postgresql.conf:\n")
        print(header)
        print(separator)
        for c in comparisons:
            print(f"   {c['setting']:<{setting_w}}  {c['recommended']:<{rec_w}}  "
                  f"{c['current']:<{cur_w}}  {c['source']:<{src_w}}  {c['status']:<{status_w}}")
        print()

    @staticmethod
    def _print_hba_audit(recommended_entries, live_rules):
        """Prints pg_hba.conf audit with current rules and recommendations."""
        print("   pg_hba.conf:\n")

        print("   Current server rules:\n")
        print(f"   {'Line':<6} {'Type':<10} {'Database':<12} {'User':<10} "
              f"{'Address':<20} {'Method':<8} {'Options'}")
        print(f"   {'─' * 80}")
        for rule in live_rules:
            databases = ','.join(rule.get('database', []) or [])
            users = ','.join(rule.get('user_name', []) or [])
            address = rule.get('address') or ''
            options = ','.join(rule.get('options') or []) if rule.get('options') else ''
            print(f"   {rule.get('line_number', ''):<6} {rule.get('type', ''):<10} "
                  f"{databases:<12} {users:<10} {address:<20} "
                  f"{rule.get('auth_method', ''):<8} {options}")
        print()

        if len(recommended_entries) > 1:
            print("   Recommended entries:\n")
            print('\n'.join(f"   {entry}" for entry in recommended_entries))
            print()
