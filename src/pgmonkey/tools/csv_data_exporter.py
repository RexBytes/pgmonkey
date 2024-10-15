import asyncio
import csv
import os
import aiofiles
import yaml
import re
import sys
from pathlib import Path
from tqdm import tqdm
from pgmonkey import PGConnectionManager


class CSVDataExporter:
    def __init__(self, config_file, table_name, csv_file=None, export_config_file=None):
        self.config_file = config_file
        self.table_name = table_name

        # Handle schema and table name
        if '.' in table_name:
            self.schema_name, self.table_name = table_name.split('.')
        else:
            self.schema_name = 'public'
            self.table_name = table_name

        # Automatically set the CSV output file name if not provided
        if not csv_file:
            self.csv_file = Path(self.table_name).with_suffix('.csv')
        else:
            self.csv_file = csv_file

        # Automatically set the export config file to the same name as the csv_file but with .yaml extension
        if not export_config_file:
            self.export_config_file = Path(self.csv_file).with_suffix('.yaml')
        else:
            self.export_config_file = export_config_file

        # Initialize the connection manager (this was missing)
        self.connection_manager = PGConnectionManager()

        # Check if the export configuration file exists
        if not os.path.exists(self.export_config_file):
            self._prepopulate_export_config()

        # Load export settings from the config file
        with open(self.export_config_file, 'r') as config_file:
            export_settings = yaml.safe_load(config_file)

        # Extract export settings from the config file
        self.has_headers = export_settings.get('has_headers', True)
        self.enforce_lowercase = export_settings.get('enforce_lowercase', True)
        self.delimiter = export_settings.get('delimiter', ',')
        self.quotechar = export_settings.get('quotechar', '"')
        self.encoding = export_settings.get('encoding', 'utf-8')

        # Extract the connection type directly from the connection config
        with open(self.config_file, 'r') as config_file:
            connection_config = yaml.safe_load(config_file)
            self.connection_type = connection_config['postgresql'].get('connection_type', 'normal')

    def _prepopulate_export_config(self):
        """Automatically creates the export config file and detects the database encoding."""
        print(f"Export config file '{self.export_config_file}' not found. Creating it with auto-detected settings.")

        # Connect to the database and retrieve the encoding
        with self.connection_manager.get_database_connection(self.config_file) as connection:
            with connection.cursor() as cur:
                # Query to detect the current database encoding
                cur.execute("SHOW client_encoding")
                db_encoding = cur.fetchone()[0]

        # Prepare the default export settings, defaulting to UTF-8 for the export
        default_config = {
            'has_headers': True,
            'auto_create_table': True,
            'enforce_lowercase': True,
            'delimiter': ',',
            'quotechar': '"',
            'encoding': 'utf-8'  # Default encoding for export
        }

        # Write the settings to the export config file
        with open(self.export_config_file, 'w') as config_file:
            yaml.dump(default_config, config_file)

            # Append comments
            config_file.write(f"# Original database encoding: {db_encoding}\n")
            config_file.write("""
    # Export configuration options:
    #
    # Booleans here can be True or False as required. 
    #
    # has_headers: Boolean - True if you want to include column headers in the CSV.
    # enforce_lowercase: Boolean - If True, the exporter will enforce lowercase and underscores in column names.
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
    """)

        print(f"Export configuration file '{self.export_config_file}' has been created.")
        print("Please review the file and adjust settings if necessary before running the export process again.")

        # Exit the process to allow the user to review the file
        sys.exit(0)

    def _format_column_names(self, headers):
        """Formats column names by lowercasing and replacing spaces with underscores."""
        if self.enforce_lowercase:
            return [header.lower().replace(" ", "_") for header in headers]
        return headers

    def _set_client_encoding(self, cur):
        """Set the client encoding only if it is different from the database's default."""
        # Get the current client encoding
        cur.execute("SHOW client_encoding")
        original_encoding = cur.fetchone()[0]

        # Set the desired encoding if different from the original one
        if self.encoding.lower() != original_encoding.lower():
            cur.execute(f"SET CLIENT_ENCODING TO '{self.encoding}'")
            print(f"Client encoding set to: {self.encoding}")
        return original_encoding

    def _restore_client_encoding(self, cur, original_encoding):
        """Restore the original client encoding after the export."""
        if self.encoding.lower() != original_encoding.lower():
            cur.execute(f"SET CLIENT_ENCODING TO '{original_encoding}'")
            print(f"Restored client encoding to: {original_encoding}")

    def _sync_export(self, connection):
        """Handles synchronous export of the table data to CSV using COPY TO with a progress bar."""
        with connection.cursor() as cur:
            # Set client encoding if necessary
            original_encoding = self._set_client_encoding(cur)

            try:
                # Get the total number of rows for the progress bar
                cur.execute(f"SELECT COUNT(*) FROM {self.schema_name}.{self.table_name}")
                total_rows = cur.fetchone()[0]

                # Open the CSV file and write data
                with open(self.csv_file, 'wb') as file:  # Open in binary mode
                    # Use the COPY TO command to stream the data from PostgreSQL
                    with cur.copy(f"COPY {self.schema_name}.{self.table_name} TO STDOUT WITH CSV HEADER") as copy:
                        with tqdm(total=total_rows, desc="Exporting data", unit="rows") as progress:
                            for data in copy:
                                file.write(data)  # Write the memoryview directly to the file
                                progress.update(1)  # Update progress bar after each chunk

                print(f"\nData from {self.schema_name}.{self.table_name} exported to {self.csv_file}.")

            finally:
                # Restore the original client encoding
                self._restore_client_encoding(cur, original_encoding)

    async def _async_export(self, connection):
        """Handles asynchronous export of the table data to CSV using COPY TO with a progress bar."""
        async with connection.cursor() as cur:
            # Set client encoding if necessary
            original_encoding = await self._set_client_encoding(cur)

            try:
                # Get the total number of rows for the progress bar
                await cur.execute(f"SELECT COUNT(*) FROM {self.schema_name}.{self.table_name}")
                total_rows = (await cur.fetchone())[0]

                # Open the CSV file asynchronously and write data
                async with aiofiles.open(self.csv_file, 'wb') as file:  # Open in binary mode
                    # Use the COPY TO command to stream the data from PostgreSQL
                    async with cur.copy(f"COPY {self.schema_name}.{self.table_name} TO STDOUT WITH CSV HEADER") as copy:
                        with tqdm(total=total_rows, desc="Exporting data", unit="rows") as progress:
                            async for data in copy:
                                await file.write(data)  # Write the memoryview directly to the file
                                progress.update(1)  # Update progress bar for each chunk

                print(f"\nData from {self.schema_name}.{self.table_name} exported to {self.csv_file}.")

            finally:
                # Restore the original client encoding
                await self._restore_client_encoding(cur, original_encoding)

    async def run(self):
        """Main method to handle connection type and start the export process."""
        if self.connection_type in ['async', 'async_pool']:
            # Async connection
            async with self.connection_manager.get_database_connection(self.config_file) as connection:
                await self._async_export(connection)
        else:
            # Sync connection
            with self.connection_manager.get_database_connection(self.config_file) as connection:
                await asyncio.to_thread(self._sync_export, connection)