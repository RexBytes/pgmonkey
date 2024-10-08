import csv
import os
import yaml
import re
import chardet
import sys
from pgmonkey import PGConnectionManager
from pathlib import Path

class CSVDataImporter:
    def __init__(self, config_file, csv_file, table_name, import_config_file=None):
        self.config_file = config_file
        self.csv_file = csv_file
        self.table_name = table_name
        # Automatically set the import config file to the same name as the csv_file but with .yaml extension
        if not import_config_file:
            self.import_config_file = Path(self.csv_file).with_suffix('.yaml')
        else:
            self.import_config_file = import_config_file

        # Check if the import configuration file exists
        if not os.path.exists(self.import_config_file):
            self._prepopulate_import_config()

        # Load import settings from the config file
        with open(self.import_config_file, 'r') as config_file:
            import_settings = yaml.safe_load(config_file)

        # Extract import settings from the config file
        self.has_headers = import_settings.get('has_headers', True)
        self.auto_create_table = import_settings.get('auto_create_table', True)
        self.enforce_lowercase = import_settings.get('enforce_lowercase', True)
        self.batch_size = import_settings.get('batch_size', 1000)
        self.delimiter = import_settings.get('delimiter', ',')
        self.quotechar = import_settings.get('quotechar', '"')
        self.encoding = import_settings.get('encoding', 'utf-8')

        # Validate that batch_size is a positive integer
        if not isinstance(self.batch_size, int) or self.batch_size <= 0:
            raise ValueError("batch_size must be a positive integer.")

        # Handle schema and table name
        if '.' in table_name:
            self.schema_name, self.table_name = table_name.split('.')
        else:
            self.schema_name = 'public'
            self.table_name = table_name

        # Initialize the connection manager
        self.connection_manager = PGConnectionManager()

    def _prepopulate_import_config(self):
        """Automatically creates the import config file by analyzing the CSV file using csv.Sniffer and guessing the encoding."""
        print(
            f"Import config file '{self.import_config_file}' not found. Creating it using csv.Sniffer and encoding detection.")

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

        # Prepare the default import settings with appended comments
        default_config = {
            'has_headers': has_headers,  # Whether the CSV file has headers. Default is True.
            'auto_create_table': True,  # Automatically create the table if it does not exist. Default is True.
            'enforce_lowercase': True,  # Enforce lowercase column names in the table. Default is True.
            #'batch_size': 1000,  # Number of rows to process in a single batch. Default is 1000.
            'delimiter': delimiter,  # Detected or defaulted CSV delimiter (e.g., ',' or ';').
            'quotechar': '"',  # Detected or defaulted quote character used in the CSV file (e.g., '"').
            'encoding': encoding  # Detected file encoding.
        }

        # Append comments
        config_comments = """
    # Import configuration options:
    #
    # Booleans here can be True or False as required. 
    #
    # has_headers: Boolean - True if the first row in the CSV contains column headers.
    # auto_create_table: Boolean - If True, the importer will automatically create the table if it doesn't exist.
    # enforce_lowercase: Boolean - If True, the importer will enforce lowercase and underscores in column names.
    # batch_size: Integer - Number of rows to process per batch during insertion.
    # delimiter: String - The character used to separate columns in the CSV file.
    # quotechar: String - The character used to quote fields containing special characters (e.g., commas).
    # encoding: String - The character encoding used by the CSV file. Below are common encodings:
    #    - utf-8: Standard encoding for most modern text, default for many systems.
    #    - iso-8859-1: Commonly used for Western European languages (English, German, French, Spanish).
    #    - iso-8859-2: Commonly used for Central and Eastern Europe languages (Polish, Czech, Hungarian, Croatian)
    #    - cp1252: Common in Windows environments for Western European languages.
    #    - utf-16: Used when working with files that have Unicode characters beyond standard utf-8.
    #    - ascii: Older encoding, supports basic English characters only.
    #
    # You can modify these settings based on the specifics of your CSV file.
    """

        # Write the settings and comments to the import config file
        with open(self.import_config_file, 'w') as config_file:
            yaml.dump(default_config, config_file)

            # Append the comments after writing the YAML content
            config_file.write(config_comments)

        print(f"Import configuration file '{self.import_config_file}' has been created.")
        print("Please review the file and adjust settings if necessary before running the import process again.")

        # Exit the process to allow the user to review the file
        sys.exit(0)

    def _format_column_names(self, headers):
        """Formats column names by lowercasing and replacing spaces with underscores."""
        formatted_headers = []
        for header in headers:
            formatted_header = header.lower().replace(" ", "_")
            if not self._is_valid_column_name(formatted_header):
                raise ValueError(f"Invalid column name '{formatted_header}'.")
            formatted_headers.append(formatted_header)
        return formatted_headers

    def _is_valid_column_name(self, column_name):
        """Validates a PostgreSQL column name. Allows numbers at the start if quoted."""
        return re.match(r'^([a-zA-Z_][a-zA-Z0-9_]*|"[0-9a-zA-Z_]+")$', column_name)

    async def _create_table(self, headers):
        """Asynchronous table creation based on CSV headers."""
        connection = await self.connection_manager.get_database_connection(self.config_file)
        async with connection as conn:
            async with conn.cursor() as cur:
                formatted_headers = self._format_column_names(headers)
                columns_definitions = ", ".join([f"{col} TEXT" for col in formatted_headers])
                create_table_query = f"CREATE TABLE {self.schema_name}.{self.table_name} ({columns_definitions})"
                await cur.execute(create_table_query)
                print(f"Table {self.schema_name}.{self.table_name} created successfully.")

    def _create_table_sync(self, headers):
        """Synchronous table creation based on CSV headers."""
        connection = self.connection_manager.get_database_connection(self.config_file)
        with connection as conn:
            with conn.cursor() as cur:
                formatted_headers = self._format_column_names(headers)
                columns_definitions = ", ".join([f"{col} TEXT" for col in formatted_headers])
                create_table_query = f"CREATE TABLE {self.schema_name}.{self.table_name} ({columns_definitions})"
                cur.execute(create_table_query)
                print(f"Table {self.schema_name}.{self.table_name} created successfully.")

    async def _check_table_exists(self, conn):
        """Asynchronous check if the table exists in the database."""
        async with conn.cursor() as cur:
            await cur.execute(f"""
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema = '{self.schema_name}' AND table_name = '{self.table_name}'
                )
            """)
            return (await cur.fetchone())[0]

    def _check_table_exists_sync(self, conn):
        """Synchronous check if the table exists in the database."""
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema = '{self.schema_name}' AND table_name = '{self.table_name}'
                )
            """)
            return cur.fetchone()[0]

    async def _async_ingest(self):
        """Handles asynchronous CSV ingestion using COPY for bulk insert."""
        connection = await self.connection_manager.get_database_connection(self.config_file)
        async with connection as conn:
            if not await self._check_table_exists(conn) and self.auto_create_table and self.has_headers:
                with open(self.csv_file, 'r', encoding=self.encoding, newline='') as file:
                    reader = csv.reader(file, delimiter=self.delimiter, quotechar=self.quotechar)
                    header = next(reader)
                    await self._create_table(header)

            # Use COPY to load data in bulk
            with open(self.csv_file, 'r', encoding=self.encoding) as file:
                if self.has_headers:
                    next(file)  # Skip header
                await conn.cursor().copy_expert(
                    f"COPY {self.schema_name}.{self.table_name} FROM STDIN WITH (FORMAT csv, DELIMITER '{self.delimiter}', QUOTE '{self.quotechar}', HEADER {self.has_headers})",
                    file)
                print(f"Data from {self.csv_file} copied to {self.table_name}.")

    def _sync_ingest(self):
        """Handles synchronous CSV ingestion using COPY for bulk insert."""
        connection = self.connection_manager.get_database_connection(self.config_file)
        with connection as conn:
            if not self._check_table_exists_sync(conn) and self.auto_create_table and self.has_headers:
                with open(self.csv_file, 'r', encoding=self.encoding, newline='') as file:
                    reader = csv.reader(file, delimiter=self.delimiter, quotechar=self.quotechar)
                    header = next(reader)
                    self._create_table_sync(header)

            # Use COPY to load data in bulk
            with open(self.csv_file, 'r', encoding=self.encoding) as file:
                if self.has_headers:
                    next(file)  # Skip header
                with conn.cursor() as cur:
                    cur.copy_expert(
                        f"COPY {self.schema_name}.{self.table_name} FROM STDIN WITH (FORMAT csv, DELIMITER '{self.delimiter}', QUOTE '{self.quotechar}', HEADER {self.has_headers})",
                        file)
                print(f"Data from {self.csv_file} copied to {self.table_name}.")

    async def run(self):
        """Determine the connection type and run the appropriate ingestion method."""
        connection_type = self.connection_manager.get_connection_type(self.config_file)

        if 'async' not in connection_type:
            return self._sync_ingest()

        return await self._async_ingest()

    def validate_table_columns(self, conn):
        """Validate that the table columns are all of type TEXT."""
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = '{self.schema_name}' AND table_name = '{self.table_name}'
            """)
            columns = cur.fetchall()
            for column_name, data_type in columns:
                if data_type.lower() != 'text':
                    raise ValueError(f"Column '{column_name}' in table '{self.table_name}' is of type '{data_type}', not TEXT.")
