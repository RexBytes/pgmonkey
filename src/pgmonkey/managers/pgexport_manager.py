import asyncio
from pgmonkey.tools.csv_data_exporter import CSVDataExporter
from pathlib import Path

class PGExportManager:
    def __init__(self):
        pass

    def export_table(self, table_name, connection_config, csv_file=None):
        # Ensure the connection config file exists
        connection_config_path = Path(connection_config)
        if not connection_config_path.exists():
            raise FileNotFoundError(f"Connection config file not found: {connection_config}")

        # Automatically create the export config file in the same directory as the CSV file (if not provided)
        if not csv_file:
            csv_file = Path(table_name).with_suffix('.csv')  # Default CSV file name from the table name

        export_config_file = Path(csv_file).with_suffix('.yaml')  # Use the same name with .yaml extension

        # Initialize the CSVDataExporter with the necessary settings
        exporter = CSVDataExporter(str(connection_config), table_name, str(csv_file), str(export_config_file))

        # Run the export process
        asyncio.run(exporter.run())

