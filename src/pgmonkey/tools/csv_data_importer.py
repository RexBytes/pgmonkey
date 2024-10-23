import asyncio
import csv
import os
import yaml
import re
import chardet
import sys
import aiofiles
from pgmonkey import PGConnectionManager
from pathlib import Path
from tqdm import tqdm
from copy import deepcopy


class CSVDataImporter:
    def __init__(self, config_file, csv_file, table_name, import_config_file=None):
        self.config_file = config_file
        self.csv_file = csv_file
        self.table_name = table_name

        # Handle schema and table name
        if '.' in table_name:
            self.schema_name, self.table_name = table_name.split('.')
        else:
            self.schema_name = 'public'
            self.table_name = table_name

        # Automatically set the import config file to the same name as the csv_file but with .yaml extension
        if not import_config_file:
            self.import_config_file = Path(self.csv_file).with_suffix('.yaml')
        else:
            self.import_config_file = import_config_file

        # Check if the import configuration file exists
        if not os.path.exists(self.import_config_file):
            self._prepopulate_import_config()

        # Initialize the connection manager
        self.connection_manager = PGConnectionManager()

        # Load import settings from the config file
        with open(self.import_config_file, 'r') as config_file:
            import_settings = yaml.safe_load(config_file)

        # Extract import settings from the config file
        self.has_headers = import_settings.get('has_headers', True)
        self.auto_create_table = import_settings.get('auto_create_table', True)
        self.enforce_lowercase = import_settings.get('enforce_lowercase', True)
        self.delimiter = import_settings.get('delimiter', ',')
        self.quotechar = import_settings.get('quotechar', '"')
        self.encoding = import_settings.get('encoding', 'utf-8')

    def modify_connection_type_for_import(self, connection_config):
        """Modify the connection type to 'normal' if it's 'async' or 'async_pool'."""
        current_type = connection_config['postgresql'].get('connection_type')

        # Check if the connection type needs to be modified
        if current_type in ['async', 'async_pool']:
            print(f"Detected connection type: {current_type}.")
            print("For import/export operations, async connections can be slower.")
            print("Switching to 'normal' connection for better performance.")

            # Deep copy the configuration so the original YAML file isn't modified
            modified_config = deepcopy(connection_config)
            modified_config['postgresql']['connection_type'] = 'normal'
            return modified_config

        return connection_config  # No change if it's already 'normal' or 'pool'

    def _prepare_header_mapping(self):
        """Reads the CSV file and prepares the header mapping, skipping leading blank lines."""
        with open(self.csv_file, 'r', encoding=self.encoding, newline='') as file:
            reader = csv.reader(file, delimiter=self.delimiter, quotechar=self.quotechar)

            # Skip leading blank lines
            header = None
            for row in reader:
                if any(row):  # This checks if the row is not empty
                    header = row
                    break

            if header is None:
                raise ValueError("The CSV file does not contain any non-empty rows.")

            self._format_column_names(header)

    def _prepopulate_import_config(self):
        """Automatically creates the import config file by analyzing the CSV file using csv.Sniffer and guessing the encoding."""
        print(f"Import config file '{self.import_config_file}' not found. Creating it using csv.Sniffer and encoding detection.")

        # Guess the file's encoding
        with open(self.csv_file, 'rb') as raw_file:
            raw_data = raw_file.read(1024)  # Read a small sample for encoding detection
            result = chardet.detect(raw_data)
            encoding = result['encoding'] or 'utf-8'  # Default to utf-8 if detection fails
            print(f"Guessed encoding: {encoding}")

        # Use csv.Sniffer to detect delimiter and headers
        try:
            with open(self.csv_file, 'r', encoding=encoding) as file:
                sample = file.read(1024)  # Read a small sample of the CSV file
                sniffer = csv.Sniffer()

                # Detect delimiter and quote character
                dialect = sniffer.sniff(sample)
                delimiter = dialect.delimiter
                has_headers = sniffer.has_header(sample)
        except csv.Error:
            print("csv.Sniffer failed to detect delimiter or quote character. Using defaults.")
            delimiter = ','
            has_headers = True

        # Prepare the default import settings
        default_config = {
            'has_headers': has_headers,
            'auto_create_table': True,
            'enforce_lowercase': True,
            'delimiter': delimiter,
            'quotechar': '"',
            'encoding': encoding
        }

        # Write the settings to the import config file
        with open(self.import_config_file, 'w') as config_file:
            yaml.dump(default_config, config_file)

            # Append comments
            config_file.write("""
    # Import configuration options:
    #
    # Booleans here can be True or False as required. 
    #
    # has_headers: Boolean - True if the first row in the CSV contains column headers.
    # auto_create_table: Boolean - If True, the importer will automatically create the table if it doesn't exist.
    # enforce_lowercase: Boolean - If True, the importer will enforce lowercase and underscores in column names.
    # delimiter: String - The character used to separate columns in the CSV file.
    #    Common delimiters include:
    #    - ',' (comma): Most common for CSV files.
    #    - ';' (semicolon): Used in some European countries.
    #    - '\\t' (tab): Useful for tab-separated files.
    #    - '|' (pipe): Used when data contains commas.
    # quotechar: String - The character used to quote fields containing special characters (e.g., commas).
    # encoding: String - The character encoding used by the CSV file. Below are common encodings:
    #    - utf-8: Standard encoding for most modern text, default for many systems.
    #    - iso-8859-1: Commonly used for Western European languages (English, German, French, Spanish).
    #    - iso-8859-2: Commonly used for Central and Eastern Europe languages (Polish, Czech, Hungarian, Croatian).
    #    - cp1252: Common in Windows environments for Western European languages.
    #    - utf-16: Used when working with files that have Unicode characters beyond standard utf-8.
    #    - ascii: Older encoding, supports basic English characters only.
    #
    # You can modify these settings based on the specifics of your CSV file.
    """)

        print(f"Import configuration file '{self.import_config_file}' has been created.")
        print("Please review the file and adjust settings if necessary before running the import process again.")

        # Exit the process to allow the user to review the file
        sys.exit(0)

    def _format_column_names(self, headers):
        """Formats column names by lowercasing and replacing spaces with underscores."""
        formatted_headers = []
        self.header_mapping = {}  # Store the mapping between original and formatted headers

        for header in headers:
            formatted_header = header.lower().replace(" ", "_")
            if not self._is_valid_column_name(formatted_header):
                raise ValueError(f"Invalid column name '{formatted_header}'.")
            self.header_mapping[header] = formatted_header
            formatted_headers.append(formatted_header)

        return formatted_headers

    def _generate_column_names(self, num_columns):
        """Generate default column names for CSV files without headers."""
        return [f"column_{i + 1}" for i in range(num_columns)]

    def _is_valid_column_name(self, column_name):
        """Validates a PostgreSQL column name. Allows numbers at the start if quoted."""
        return re.match(r'^([a-zA-Z_][a-zA-Z0-9_]*|"[0-9a-zA-Z_]+")$', column_name)

    def _create_table_sync(self, connection, formatted_headers):
        """Synchronous table creation based on formatted CSV headers."""
        with connection.cursor() as cur:
            columns_definitions = ", ".join([f"{col} TEXT" for col in formatted_headers])
            create_table_query = f"CREATE TABLE {self.schema_name}.{self.table_name} ({columns_definitions})"
            cur.execute(create_table_query)

    def _sync_ingest(self, connection):
        """Handles synchronous CSV ingestion using COPY for bulk insert, properly counting non-empty rows."""
        with connection.cursor() as cur:
            # Open the CSV file to prepare for ingestion
            with open(self.csv_file, 'r', encoding=self.encoding, newline='') as file:
                reader = csv.reader(file, delimiter=self.delimiter, quotechar=self.quotechar)

                # Skip leading blank lines to find the header or first row
                header = None
                for row in reader:
                    if any(row):
                        header = row
                        break

                if header is None:
                    raise ValueError("The CSV file does not contain any non-empty rows.")

                if self.has_headers:
                    formatted_headers = self._format_column_names(header)
                    print("\nCSV Headers (Original):")
                    print(header)
                    print("\nFormatted Headers for DB:")
                    print(formatted_headers)
                else:
                    num_columns = len(header)
                    formatted_headers = self._generate_column_names(num_columns)  # Generate column_1, column_2, etc.
                    file.seek(0)  # Reset file to the start

                # Include the schema name in the output
                print(f"\nStarting import for file: {self.csv_file} into table: {self.schema_name}.{self.table_name}")

                if not self._check_table_exists_sync(connection):
                    # If no table exists, create it based on the headers
                    self._create_table_sync(connection, formatted_headers)
                    print(f"\nTable {self.schema_name}.{self.table_name} created successfully.")
                else:
                    cur.execute(
                        f"SELECT column_name FROM information_schema.columns WHERE table_schema = '{self.schema_name}' AND table_name = '{self.table_name}' ORDER BY ordinal_position")
                    existing_columns = [row[0] for row in cur.fetchall()]
                    if formatted_headers != existing_columns:
                        raise ValueError(
                            f"CSV headers do not match the existing table columns.\n"
                            f"Expected columns: {existing_columns}\n"
                            f"CSV headers: {formatted_headers}"
                        )

                # Count non-empty rows for progress bar
                total_lines = sum(1 for row in reader if any(row))
                file.seek(0)
                # Skip leading blank lines again
                for row in reader:
                    if any(row):
                        break

                with tqdm(total=total_lines, desc="Importing data", unit="rows") as progress:
                    with cur.copy(
                            f"COPY {self.schema_name}.{self.table_name} ({', '.join(formatted_headers)}) FROM STDIN") as copy:
                        for row in reader:
                            if not any(row):
                                continue
                            copy.write_row(row)
                            progress.update(1)

                connection.commit()

                # Check row count after COPY
                cur.execute(f"SELECT COUNT(*) FROM {self.schema_name}.{self.table_name}")
                row_count = cur.fetchone()[0]
                print(f"\nRow count after COPY: {row_count}")

            print(f"\nData from {self.csv_file} copied to {self.schema_name}.{self.table_name}.")

    def _check_table_exists_sync(self, connection):
        """Synchronous check if the table exists in the database."""
        with connection.cursor() as cur:
            cur.execute(f"""
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema = '{self.schema_name}' AND table_name = '{self.table_name}'
                )
            """)
            return cur.fetchone()[0]

    async def run(self):
        """Main method to handle connection type and start the ingestion."""
        # Load the YAML file into a dictionary
        with open(self.config_file, 'r') as f:
            connection_config = yaml.safe_load(f)

        # Modify the connection type for import if needed (ensure it's called once)
        connection_config = self.modify_connection_type_for_import(connection_config)

        # Extract the modified connection type
        connection_type = connection_config['postgresql'].get('connection_type', 'normal')

        # Check if the connection is async or sync
        if connection_type in ['async', 'async_pool']:
            # Async connection: await the async operations
            async with self.connection_manager.get_database_connection_from_dict(connection_config) as connection:
                await self._async_ingest(connection)
        else:
            # Sync connection: run the sync ingest with a normal context manager (no async)
            with self.connection_manager.get_database_connection_from_dict(connection_config) as connection:
                self._sync_ingest(connection)  # Blocking sync ingest

