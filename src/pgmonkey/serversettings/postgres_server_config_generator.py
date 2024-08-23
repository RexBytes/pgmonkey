import yaml

class PostgresServerConfigGenerator:
    def __init__(self, yaml_file_path):
        self.yaml_file_path = yaml_file_path
        self.config = self.read_yaml()  # Read the configuration file upon instantiation

    def read_yaml(self):
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

    def generate_pg_hba_entry(self):
        """Generates entries for pg_hba.conf based on the SSL settings, with headers for each column."""
        host = self.config['postgresql']['connection_settings']['host']
        sslmode = self.config['postgresql']['connection_settings'].get('sslmode', 'prefer')
        entries = []
        header = "TYPE  DATABASE  USER  ADDRESS          METHOD  OPTIONS"
        entries.append(header)
        if sslmode in ['verify-ca', 'verify-full']:
            clientcert = 'verify-full' if sslmode == 'verify-full' else 'verify-ca'
            ip_subnet = '.'.join(host.split('.')[:-1]) + '.0/24'  # Assuming a /24 subnet
            entry = f"hostssl all     all   {ip_subnet}    md5     clientcert={clientcert}"
            entries.append(entry)
        elif sslmode != 'disable':
            ip_subnet = '.'.join(host.split('.')[:-1]) + '.0/24'  # Assuming a /24 subnet
            entry = f"host    all     all   {ip_subnet}    reject"
            entries.append(entry)
        return entries

    def generate_postgresql_conf(self):
        """Generates minimal entries for postgresql.conf to ensure compatibility based on connection pooling settings."""
        settings = []
        connection_type = self.config['postgresql']['connection_type']
        if connection_type in ['pool', 'async_pool']:
            pool_settings = self.config['postgresql'].get('pool_settings', {})
            max_size = pool_settings.get('max_size', 100)
            max_connections = int(max_size * 1.1)
            settings.append(f"max_connections = {max_connections}")
        else:
            settings.append("max_connections = 20")

        # Generate SSL settings
        settings.extend(self.generate_ssl_settings())
        return settings

    def generate_ssl_settings(self):
        """Generates SSL configuration entries for postgresql.conf based on client settings."""
        ssl_settings = []
        if 'sslmode' in self.config['postgresql']['connection_settings'] and self.config['postgresql']['connection_settings']['sslmode'] != 'disable':
            ssl_settings.append("ssl = on")
            ssl_settings.append(f"ssl_cert_file = 'server.crt'")
            ssl_settings.append(f"ssl_key_file = 'server.key'")
            ssl_settings.append(f"ssl_ca_file = 'ca.crt'")
        return ssl_settings

    def print_configurations(self):
        """Prints the generated server configurations and provides final instructions if configurations are suggested."""
        if self.config:
            pg_hba_entries = self.generate_pg_hba_entry()
            postgresql_conf_entries = self.generate_postgresql_conf()
            print("1) Database type detected: PostgreSQL\n")
            print("2) Minimal database server settings needed for this config file:\n")

            # Print pg_hba.conf configurations if they exist
            if len(pg_hba_entries) > 1:  # More than just the header
                print("   a) pg_hba.conf:" + "\n")
                print('\n'.join(pg_hba_entries) + "\n")
            else:
                print("   a) No entries needed for pg_hba.conf.\n")

            # Print postgresql.conf configurations if they exist
            if postgresql_conf_entries:
                print("   b) postgresql.conf:" + "\n")
                print('\n'.join(postgresql_conf_entries))
            else:
                print("   b) No entries needed for postgresql.conf.\n")

            # Add a newline before final instructions
            print()  # This adds the desired newline

            # Determine which configuration files had suggestions and list them appropriately
            files_to_check = []
            if len(pg_hba_entries) > 1:
                files_to_check.append("pg_hba.conf")
            if postgresql_conf_entries:
                files_to_check.append("postgresql.conf")

            if files_to_check:
                print(f"Please check the following files on your system and ensure that the appropriate settings are applied: {', '.join(files_to_check)}.")
                print("Ensure that the network ADDRESS matches your network subnet and review all configurations.")
        else:
            print("Configuration data is not available. Please check the file path and contents.")



