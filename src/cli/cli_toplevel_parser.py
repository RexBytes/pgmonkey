import argparse
from pgmonkey.managers.toplevel_manager import ToplevelManager


def cli_toplevel_parser():
    parser = top_level_parser_init()
    parser = top_level_parser_arguments(parser)
    return parser


def top_level_parser_init():
    # Let's create the main top-level parser,
    parser = argparse.ArgumentParser(
        # prog: whenever the automatically generated help messages are displayed it will
        #       use the string value to refer to the application.
        prog='pgmonkey',
        # description: this is the description of your application.
        description="pgmonkey: A tool to assist with database connections and manage data."
    )

    return parser


def top_level_parser_arguments(parser):
    parser.add_argument(
        # add --version argument to the top level parser.
        '--version',
        # The 'version' action is a builtin argparse action specific for versioning info.
        action='version',
        # Construct a string with version information that will be returned.
        # Here we use the VersionManager class.
        # We also use the prog string we defined in the top-level parser creation above.
        version=f"%(prog)s {ToplevelManager.get_package_version('pgmonkey')}"
    )
    return parser
