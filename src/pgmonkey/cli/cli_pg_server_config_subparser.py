from pgmonkey.managers.pg_server_config_manager import PGServerConfigManager


def cli_pg_server_config_subparser(subparsers):
    pg_server_config_manager = PGServerConfigManager()

    pg_server_config_parser = subparsers.add_parser('pgserverconfig',
                                                    help='Generate suggested server configuration entries')

    pg_server_config_parser.add_argument('--filepath', required=True,
                                         help='Path to the config you want settings generated.')
    pg_server_config_parser.add_argument('--audit', action='store_true', default=False,
                                         help='Connect to the server and compare current settings '
                                              'against recommendations.')
    pg_server_config_parser.set_defaults(func=pg_server_config_create_handler,
                                         pg_server_config_manager=pg_server_config_manager)


def pg_server_config_create_handler(args):
    pg_server_config_manager = args.pg_server_config_manager

    if args.audit:
        pg_server_config_manager.audit_server_config(args.filepath)
    else:
        pg_server_config_manager.get_server_config(args.filepath)
