import asyncio
from pgmonkey.tools.csv_data_importer import CSVDataImporter
from pathlib import Path

class PGImportManager:
    def __init__(self):
        pass

    def import_file(self, csv_file, table_name, connection_config):
        # Ensure the connection config file exists
        connection_config_path = Path(connection_config)
        if not connection_config_path.exists():
            raise FileNotFoundError(f"Connection config file not found: {connection_config}")

        # Automatically create the import config file in the same directory as the CSV file
        import_config_file = Path(csv_file).with_suffix('.yaml')  # Use the same name with .yaml extension

        # Initialize the CSVDataImporter with the necessary settings
        importer = CSVDataImporter(str(connection_config), str(csv_file), table_name, str(import_config_file))

        # Run the import process
        asyncio.run(importer.run())
