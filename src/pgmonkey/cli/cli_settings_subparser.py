import argparse
from pgmonkey.managers.settings_manager import SettingsManager


def cli_settings_subparser(subparsers):
    # Create a subparser for the settings command
    subparser = subparsers.add_parser('settings', help='Manage application settings.')

    # Add arguments specific to the settings management
    subparser.add_argument("--helloworld", type=str, help="Place holder for settings subparser")

    # Set the default function to call with parsed arguments
    subparser.set_defaults(func=settings_subparser_handle)


def settings_subparser_handle(args):
    settings_manager = SettingsManager()

    if args.helloworld:
        settings_manager.print_hello_world()
