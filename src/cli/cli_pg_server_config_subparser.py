from pgmonkey.managers.pg_server_config_manager import PGServerConfigManager


def cli_pg_server_config_subparser(subparsers):
    pg_server_config_manager = PGServerConfigManager()

    pg_server_config_parser = subparsers.add_parser('pgserverconfig',
                                                    help='Generate suggested server configuration entries')

    pg_server_config_parser.add_argument('--filepath', required=True,
                                         help='Path to the config you want settings generated.')
    pg_server_config_parser.set_defaults(func=pg_server_config_create_handler,
                                         pg_server_config_manager=pg_server_config_manager)


def pg_server_config_create_handler(args):
    pg_server_config_manager = args.pg_server_config_manager

    if args.filepath:
        pg_server_config_manager.get_server_config(args.filepath)
