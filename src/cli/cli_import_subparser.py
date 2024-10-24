from pgmonkey.managers.pgimport_manager import PGImportManager
from pathlib import Path

def cli_pgimport_subparser(subparsers):
    pgimport_manager = PGImportManager()

    # Define the 'pgimport' subcommand
    pgimport_parser = subparsers.add_parser('pgimport', help='Import CSV and text files to the PostgreSQL database')

    # Required arguments: CSV file to import, table name, and connection config
    pgimport_parser.add_argument('--import_file', type=str, required=True, help='Path to the file to import.')
    pgimport_parser.add_argument('--table', type=str, required=True, help='Name of the target table in the database (schema.table or table).')
    pgimport_parser.add_argument('--connconfig', type=str, required=True, help='Path to the connection config file.')

    # Set the default function to handle the import command
    pgimport_parser.set_defaults(func=pgimport_handler, pgimport_manager=pgimport_manager)


def pgimport_handler(args):
    pgimport_manager = args.pgimport_manager

    # Get the path of the CSV file
    import_file = Path(args.import_file)

    # Ensure the CSV file exists before proceeding
    if not import_file.exists():
        print(f"Import file not found: {import_file}")
        return

    # Get the table name provided by the user
    table_name = args.table

    # Get the mandatory connection config file
    connection_config = Path(args.connconfig)

    if not connection_config.exists():
        print(f"Connection config file not found: {connection_config}")
        return

    # Proceed with importing the file (the settings file is automatically derived)
    # print(f"Starting import for file: {import_file} into table: {table_name}")
    pgimport_manager.import_file(import_file, table_name, connection_config)
    print("Import complete.")

