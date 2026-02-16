import csv
import os
import yaml
import re
import chardet
import sys
from psycopg import sql
from pgmonkey import PGConnectionManager
from pathlib import Path
from tqdm import tqdm
from pgmonkey.common.utils.configutils import normalize_config


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

    @staticmethod
    def _resolve_import_connection_type(connection_config):
        """Determine the best connection type for import operations.

        Import uses 'normal' sync connections for best performance with COPY.
        """
        current_type = connection_config.get('connection_type', 'normal')
        if current_type in ('async', 'async_pool'):
            print(f"Detected connection type: {current_type}.")
            print("For import operations, switching to 'normal' connection for better performance.")
        return 'normal'

    def _detect_bom(self):
        """Detects BOM encoding from the start of the file."""
        with open(self.csv_file, 'rb') as f:
            first_bytes = f.read(4)
            # Check longer BOMs first: UTF-32 BOMs start with the same bytes as UTF-16
            if first_bytes.startswith(b'\xff\xfe\x00\x00'):
                return 'utf-32-le'
            elif first_bytes.startswith(b'\x00\x00\xfe\xff'):
                return 'utf-32-be'
            elif first_bytes.startswith(b'\xef\xbb\xbf'):
                return 'utf-8-sig'
            elif first_bytes.startswith(b'\xff\xfe'):
                return 'utf-16-le'
            elif first_bytes.startswith(b'\xfe\xff'):
                return 'utf-16-be'
        return None

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
        """Automatically creates the import config file by analyzing the CSV file using robust encoding detection."""
        print(
            f"Import config file '{self.import_config_file}' not found. Creating it using advanced encoding detection.")

        # Detect BOM encoding first
        encoding = self._detect_bom()
        if encoding:
            print(f"Detected BOM encoding: {encoding}")
        else:
            # Fallback to chardet with a larger sample
            with open(self.csv_file, 'rb') as raw_file:
                raw_data = raw_file.read(65536)  # Read a large sample for better detection
                result = chardet.detect(raw_data)
                encoding = result['encoding'] or 'utf-8'
                confidence = result['confidence']
                print(f"Detected encoding: {encoding} with confidence: {confidence}")

                # Fallback to UTF-8 if chardet's confidence is low
                if confidence < 0.5:
                    print("Low confidence in detected encoding. Falling back to UTF-8.")
                    encoding = 'utf-8'

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
            # Skip columns where the header is completely empty
            if not header.strip():
                print(f"Skipping empty column at index {headers.index(header)}")
                continue
            # Replace invalid characters with underscores
            formatted_header = re.sub(r'[^a-zA-Z0-9_]', '_', header.lower())
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

    def _qualified_table(self):
        """Returns a properly quoted schema.table SQL composable."""
        return sql.SQL("{}.{}").format(
            sql.Identifier(self.schema_name),
            sql.Identifier(self.table_name),
        )

    def _create_table_sync(self, connection, formatted_headers):
        """Synchronous table creation based on formatted CSV headers."""
        with connection.cursor() as cur:
            columns = sql.SQL(", ").join(
                sql.SQL("{} TEXT").format(sql.Identifier(col))
                for col in formatted_headers
            )
            query = sql.SQL("CREATE TABLE {} ({})").format(
                self._qualified_table(), columns
            )
            cur.execute(query)

    def _sync_ingest(self, connection):
        """Handles synchronous CSV ingestion using COPY for bulk insert, properly counting non-empty rows."""
        # Increase the CSV field size limit
        import csv
        import sys
        max_int = sys.maxsize
        while True:
            try:
                csv.field_size_limit(max_int)
                break
            except OverflowError:
                max_int = int(max_int / 10)

        with connection.cursor() as cur:
            # Open the CSV file to prepare for ingestion
            # Open file and read first few lines to detect column count
            with open(self.csv_file, 'r', encoding=self.encoding, newline='') as file:
                sample_rows = [next(file).strip() for _ in range(5)]  # Read first 5 rows
                sample_splits = [row.split(self.delimiter) for row in sample_rows]
                column_counts = [len(split) for split in sample_splits if any(split)]  # Ignore empty lines

                # Determine if it's a single-column CSV
                is_single_column = all(count == 1 for count in column_counts)
                print(f"Detected column structure: {column_counts}. Single-column file? {is_single_column}")

            # Step 2: Override delimiter if it's a single-column file
            if is_single_column:
                print("Single-column CSV detected. Ignoring delimiter.")
                self.delimiter = None  # Disable delimiter-based parsing

            print(f"Using delimiter: {repr(self.delimiter)}")  # Debugging log

            # Step 3: Open file again with adjusted delimiter setting
            with open(self.csv_file, 'r', encoding=self.encoding, newline='') as file:
                if self.delimiter:
                    reader = csv.reader(file, delimiter=self.delimiter, quotechar=self.quotechar)
                else:
                    reader = csv.reader(file, quotechar=self.quotechar)  # No delimiter for single-column files

                # Debugging output to check first row
                for row in reader:
                    print(f"First row: {row}, Length: {len(row)}")
                    break  # Only print first row

                file.seek(0)  # Reset file position after debug print
                # Skip leading blank lines to find the header or first row
                header = None
                for row in reader:
                    if any(row):
                        header = row
                        break

                if header is None:
                    raise ValueError("The CSV file does not contain any non-empty rows.")

                # Initialize valid_indexes before using it
                valid_indexes = []

                if self.has_headers:
                    # Identify indexes of non-empty columns
                    valid_indexes = [i for i, h in enumerate(header) if h.strip()]
                    filtered_header = [header[i] for i in valid_indexes]

                    if not filtered_header:
                        raise ValueError("No valid columns detected after filtering empty headers.")

                    formatted_headers = self._format_column_names(filtered_header)
                    print(f"Final Headers (after removing empty columns): {formatted_headers}")
                    print("\nCSV Headers after removing any empty columns (Original):")
                    print(header)
                    print("\nFormatted Headers for DB:")
                    print(formatted_headers)
                else:
                    num_columns = len(header)
                    formatted_headers = self._generate_column_names(num_columns)  # Generate column_1, column_2, etc.
                    file.seek(0)  # Reset file to the start

                    valid_indexes = list(range(num_columns))

                # Include the schema name in the output
                print(f"\nStarting import for file: {self.csv_file} into table: {self.schema_name}.{self.table_name}")

                if not self._check_table_exists_sync(connection):
                    # If no table exists, create it based on the headers
                    self._create_table_sync(connection, formatted_headers)
                    print(f"\nTable {self.schema_name}.{self.table_name} created successfully.")
                else:
                    cur.execute(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_schema = %s AND table_name = %s "
                        "ORDER BY ordinal_position",
                        (self.schema_name, self.table_name),
                    )
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

                # Create Copy Command using safe SQL composition
                col_ids = sql.SQL(", ").join(
                    sql.Identifier(col) for col in formatted_headers
                )
                copy_sql = sql.SQL("COPY {} ({}) FROM STDIN").format(
                    self._qualified_table(), col_ids
                )
                copy_sql_str = copy_sql.as_string(cur)
                print(f"Executing COPY command: {copy_sql_str}")

                with tqdm(total=total_lines, desc="Importing data", unit="rows") as progress:
                    with cur.copy(copy_sql_str) as copy:
                        for row in reader:
                            if not any(row):
                                continue
                            # Ensure empty columns are removed from each row, using valid indexes
                            filtered_row = [row[i] if i < len(row) else '' for i in valid_indexes]

                            # Check row length before inserting
                            if len(filtered_row) != len(formatted_headers):
                                raise ValueError(
                                    f"Row length mismatch: Expected {len(formatted_headers)} columns, got {len(filtered_row)} - Row: {row}"
                                )
                            copy.write_row(filtered_row)
                            progress.update(1)

                connection.commit()

                # Check row count after COPY
                count_query = sql.SQL("SELECT COUNT(*) FROM {}").format(
                    self._qualified_table()
                )
                cur.execute(count_query)
                row_count = cur.fetchone()[0]
                print(f"\nRow count after COPY: {row_count}")

        print(f"\nData from {self.csv_file} copied to {self.schema_name}.{self.table_name}.")

    def _check_table_exists_sync(self, connection):
        """Synchronous check if the table exists in the database."""
        with connection.cursor() as cur:
            cur.execute(
                "SELECT EXISTS ("
                "  SELECT 1 FROM information_schema.tables"
                "  WHERE table_schema = %s AND table_name = %s"
                ")",
                (self.schema_name, self.table_name),
            )
            return cur.fetchone()[0]

    async def run(self):
        """Main method to start the ingestion using a normal sync connection for best COPY performance."""
        with open(self.config_file, 'r') as f:
            connection_config = yaml.safe_load(f)

        connection_config = normalize_config(connection_config)
        conn_type = self._resolve_import_connection_type(connection_config)
        connection = self.connection_manager.get_database_connection_from_dict(connection_config, conn_type)

        with connection as conn:
            self._sync_ingest(conn)
