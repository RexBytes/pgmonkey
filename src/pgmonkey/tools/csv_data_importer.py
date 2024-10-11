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
from tqdm.asyncio import tqdm as tqdm_async

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
        self.batch_size = import_settings.get('batch_size', 1000)
        self.delimiter = import_settings.get('delimiter', ',')
        self.quotechar = import_settings.get('quotechar', '"')
        self.encoding = import_settings.get('encoding', 'utf-8')

        # Extract the connection type directly from the connection config
        with open(self.config_file, 'r') as config_file:
            connection_config = yaml.safe_load(config_file)
            self.connection_type = connection_config['postgresql'].get('connection_type', 'normal')

    def _prepare_header_mapping(self):
        """Reads the CSV file and prepares the header mapping."""
        with open(self.csv_file, 'r', encoding=self.encoding, newline='') as file:
            reader = csv.reader(file, delimiter=self.delimiter, quotechar=self.quotechar)
            header = next(reader)
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

        # Prepare the default import settings with appended comments
        default_config = {
            'has_headers': has_headers,
            'auto_create_table': True,
            'enforce_lowercase': True,
            'delimiter': delimiter,
            'quotechar': '"',
            'encoding': encoding
        }

        # Write the settings and comments to the import config file
        with open(self.import_config_file, 'w') as config_file:
            yaml.dump(default_config, config_file)

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
            #print(f"Table {self.schema_name}.{self.table_name} created successfully.")

    async def _create_table_async(self, connection, formatted_headers):
        """Asynchronous table creation based on formatted CSV headers."""
        async with connection.cursor() as cur:
            columns_definitions = ", ".join([f"{col} TEXT" for col in formatted_headers])
            create_table_query = f"CREATE TABLE {self.schema_name}.{self.table_name} ({columns_definitions})"
            await cur.execute(create_table_query)
            #print(f"Table {self.schema_name}.{self.table_name} created successfully.")

    def _sync_ingest(self, connection):
        """Handles synchronous CSV ingestion using COPY for bulk insert."""
        with connection.cursor() as cur:
            # Open the CSV file to prepare for ingestion
            with open(self.csv_file, 'r', encoding=self.encoding, newline='') as file:
                reader = csv.reader(file, delimiter=self.delimiter, quotechar=self.quotechar)

                if self.has_headers:
                    header = next(reader)  # Read the header row
                    formatted_headers = self._format_column_names(header)
                    print("\nCSV Headers (Original):")
                    print(header)
                    print("\nFormatted Headers for DB:")
                    print(formatted_headers)
                else:
                    first_row = next(reader)
                    num_columns = len(first_row)
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
                        raise ValueError(f"CSV headers do not match existing table columns: {existing_columns}")

                # Count rows for progress bar
                total_lines = sum(1 for row in reader)
                file.seek(0)
                if self.has_headers:
                    next(reader)  # Skip the header row

                with tqdm(total=total_lines, desc="Importing data", unit="rows") as progress:
                    with cur.copy(
                            f"COPY {self.schema_name}.{self.table_name} ({', '.join(formatted_headers)}) FROM STDIN") as copy:
                        for row in reader:
                            copy.write_row(row)
                            progress.update(1)  # Update progress bar after each row

                connection.commit()

                # Check row count after COPY
                cur.execute(f"SELECT COUNT(*) FROM {self.schema_name}.{self.table_name}")
                row_count = cur.fetchone()[0]
                print(f"\nRow count after COPY: {row_count}")

            print(f"\nData from {self.csv_file} copied to {self.schema_name}.{self.table_name}.")

    async def _async_ingest(self, connection):
        """Handles asynchronous CSV ingestion using COPY for bulk insert."""
        async with connection.cursor() as cur:
            async with aiofiles.open(self.csv_file, mode='r', encoding=self.encoding) as file:
                reader = csv.reader(await file.readline(), delimiter=self.delimiter, quotechar=self.quotechar)

                if self.has_headers:
                    header = next(reader)  # Read the header row
                    formatted_headers = self._format_column_names(header)
                    print("\nCSV Headers (Original):")
                    print(header)
                    print("\nFormatted Headers for DB:")
                    print(formatted_headers)
                else:
                    first_row = next(reader)
                    num_columns = len(first_row)
                    formatted_headers = self._generate_column_names(num_columns)
                    await file.seek(0)

                # Include the schema name in the output
                print(f"\nStarting import for file: {self.csv_file} into table: {self.schema_name}.{self.table_name}")

                if not await self._check_table_exists_async(connection):
                    await self._create_table_async(connection, formatted_headers)
                    print(f"\nTable {self.schema_name}.{self.table_name} created successfully.")
                else:
                    await cur.execute(
                        f"SELECT column_name FROM information_schema.columns WHERE table_schema = '{self.schema_name}' AND table_name = '{self.table_name}' ORDER BY ordinal_position")
                    existing_columns = [row[0] for row in await cur.fetchall()]
                    if formatted_headers != existing_columns:
                        raise ValueError(f"CSV headers do not match existing table columns: {existing_columns}")

                total_lines = sum(1 for row in reader)
                await file.seek(0)
                if self.has_headers:
                    await file.readline()  # Skip the header row

                async with tqdm(total=total_lines, desc="Importing data", unit="rows") as progress:
                    async with cur.copy(
                            f"COPY {self.schema_name}.{self.table_name} ({', '.join(formatted_headers)}) FROM STDIN") as copy:
                        for row in reader:
                            await copy.write_row(row)
                            progress.update(1)  # Update progress bar after each row

                await connection.commit()

                # Check row count after COPY
                await cur.execute(f"SELECT COUNT(*) FROM {self.schema_name}.{self.table_name}")
                row_count = await cur.fetchone()[0]
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

    async def _check_table_exists_async(self, connection):
        """Asynchronous check if the table exists in the database."""
        async with connection.cursor() as cur:
            await cur.execute(f"""
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema = '{self.schema_name}' AND table_name = '{self.table_name}'
                )
            """)
            return await cur.fetchone()[0]

    async def run(self):
        """Main method to handle connection type and start the ingestion."""
        if self.connection_type in ['async', 'async_pool']:
            # Async connection
            async with self.connection_manager.get_database_connection(self.config_file) as connection:
                await self._async_ingest(connection)
        else:
            # Sync connection
            with self.connection_manager.get_database_connection(self.config_file) as connection:
                await asyncio.to_thread(self._sync_ingest, connection)




