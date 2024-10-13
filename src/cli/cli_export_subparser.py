from pgmonkey.managers.pgexport_manager import PGExportManager
from pathlib import Path


def cli_pgexport_subparser(subparsers):
    pgexport_manager = PGExportManager()

    # Define the 'pgexport' subcommand
    pgexport_parser = subparsers.add_parser('pgexport', help='Export PostgreSQL table data to a CSV file')

    # Required arguments: table name and connection config
    pgexport_parser.add_argument('--table', type=str, required=True,
                                 help='Name of the source table in the database (schema.table or table).')
    pgexport_parser.add_argument('--connconfig', type=str, required=True, help='Path to the connection config file.')

    # Optional argument: CSV file to export data to (if not provided, a default is used)
    pgexport_parser.add_argument('--export_file', type=str,
                                 help='Path to the CSV file to export to (default: based on table name).')

    # Set the default function to handle the export command
    pgexport_parser.set_defaults(func=pgexport_handler, pgexport_manager=pgexport_manager)


def pgexport_handler(args):
    pgexport_manager = args.pgexport_manager

    # Get the table name provided by the user
    table_name = args.table

    # Get the mandatory connection config file
    connection_config = Path(args.connconfig)

    if not connection_config.exists():
        print(f"Connection config file not found: {connection_config}")
        return

    # Optional: Get the CSV export file path (if provided)
    export_file = None
    if args.export_file:
        export_file = Path(args.export_file)

    # Proceed with exporting the table data to CSV (the export settings file is automatically derived)
    # print(f"Starting export of table: {table_name} to CSV file: {export_file if export_file else 'default based on table name'}")
    pgexport_manager.export_table(table_name, connection_config, export_file)
    print("Export complete.")
