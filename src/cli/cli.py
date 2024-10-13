import sys
from .cli_toplevel_parser import cli_toplevel_parser
from .cli_settings_subparser import cli_settings_subparser
from .cli_pgconfig_subparser import cli_pgconfig_subparser
from .cli_pg_server_config_subparser import  cli_pg_server_config_subparser
from .cli_import_subparser import cli_pgimport_subparser
from .cli_export_subparser import cli_pgexport_subparser


class CLI:
    def __init__(self):
        # We need the main top level parser.
        self.parser = cli_toplevel_parser()
        # We attach a 'sub-parser container' to hold all subparsers, e.g. the subparser that handles settings.
        self.subparsers = self.parser.add_subparsers(title="commands", dest="command", help="Available commands")
        # We start populating the 'sub-parser container' with subparsers.
        cli_settings_subparser(self.subparsers)
        cli_pgconfig_subparser(self.subparsers)
        cli_pg_server_config_subparser(self.subparsers)
        cli_pgimport_subparser(self.subparsers)
        cli_pgexport_subparser(self.subparsers)

    def run(self):
        # Parse all arguments from the command line into argparse.
        args = self.parser.parse_args()

        # If no command is provided, print help
        if len(sys.argv) == 1:
            self.parser.print_help(sys.stderr)
            sys.exit(1)
        # This bit here feels like magic, let me explain.
        # You already have defined parser and subparser logic which the argparse module understands.
        # If you give it say "pgmonkey settings --helloworld" it knows it needs to looks at your
        # settings subparser, and it knows you have given it --helloworld argument.
        # It looks at all the arguments you have given, and the associated default
        # arguments, in this case func=settings_subparser_handle.
        #
        # The following if statement merely checks if the argument func has been populated,
        # it then calls the function and passes in all the other arguments.
        # The argument helloworld is detected and acted on by the function settings_subparser_handle()
        # This is a very flexible implementation, which is why it feels like magic.
        if hasattr(args, 'func'):
            args.func(args)
        else:
            self.parser.print_help()


def main():
    cli = CLI()
    cli.run()


if __name__ == "__main__":
    main()
