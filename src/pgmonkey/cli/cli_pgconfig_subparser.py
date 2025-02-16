from pgmonkey.managers.pgconfig_manager import PGConfigManager
from pgmonkey.managers.pgcodegen_manager import PGCodegenManager
from pathlib import Path


def cli_pgconfig_subparser(subparsers):
    pgconfig_manager = PGConfigManager()
    pgcodegen_manager = PGCodegenManager()

    pgconfig_parser = subparsers.add_parser('pgconfig', help='Manage database configurations')
    # Note, the following line is adding a subparser to this subparser which is allowed.
    pgconfig_subparsers = pgconfig_parser.add_subparsers(dest='pgconfig_command', help='pgconfig commands')

    # The "create" subcommand
    create_parser = pgconfig_subparsers.add_parser('create', help='Create a new database configuration file.')
    create_parser.add_argument('--type', choices=['pg'], default='pg', required=False,
                               help='Database type for the configuration template. Default is "pg".')
    # Adding alias: --connconfig for --filepath
    create_parser.add_argument('--filepath', '--connconfig', required=True,
                               help='Path to where you want your configuration file created.')
    create_parser.set_defaults(func=pgconfig_create_handler, pgconfig_manager=pgconfig_manager)

    # The "test" subcommand
    test_parser = pgconfig_subparsers.add_parser('test',
                                                 help='Test the database connection using a configuration file.')
    # Adding alias: --connconfig for --filepath
    test_parser.add_argument('--filepath', '--connconfig', required=True,
                             help='Path to the configuration file you want to test.')
    test_parser.set_defaults(func=pgconfig_test_handler, pgconfig_manager=pgconfig_manager)

    # The "generate-code" subcommand
    code_parser = pgconfig_subparsers.add_parser('generate-code', help='Generate Python code to connect using a configuration file.')
    # Adding alias: --connconfig for --filepath
    code_parser.add_argument('--filepath', '--connconfig', required=True,
                             help='Path to the configuration file you want to use.')
    code_parser.set_defaults(func=pgconfig_generate_code_handler, pgcodegen_manager=pgcodegen_manager)


def pgconfig_create_handler(args):
    pgconfig_manager = args.pgconfig_manager
    filepath = Path(args.filepath)
    if filepath.exists():
        print(f'Configuration file already exists: {filepath}\nEdit this file to update settings.')
    else:
        config_template_text = pgconfig_manager.get_config_template_text(args.type)
        pgconfig_manager.write_config_template_text(filepath, config_template_text)


def pgconfig_test_handler(args):
    pgconfig_manager = args.pgconfig_manager
    pgconfig_manager.test_connection(args.filepath)

def pgconfig_generate_code_handler(args):
    pgcodegen_manager = args.pgcodegen_manager
    pgcodegen_manager.generate_connection_code(args.filepath)

