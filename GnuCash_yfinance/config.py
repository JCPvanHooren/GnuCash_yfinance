"""Module to process configuration variables

If run as main module (not imported): print configuration variables

Process arguments from cli and config.ini

1. Parse cli arguments, including default assertion as per ArgumentParser
2. Collect default values from `config.ini`
3. Set final configuration variables in order of precedence:

    1. Arguments provided on cli
    2. If not defined on cli: default provided as per ArgumentParser
    3. If not defined in ArgumentParser: from `config.ini`
    4. If not provided on cli, nor in `config.ini`: hardcoded defaults OR exit script if needed

Tip:
    All options can have a default set by adding the 'long' key in `config.ini`


.. _Google Python Style Guide:
   http://google.github.io/styleguide/pyguide.html

"""

import sys
import argparse
import configparser
import getpass
from collections import ChainMap
from datetime import date
from dataclasses import dataclass, fields, InitVar

import helpers

@dataclass
class GeneralConfig:
    """Class to store 'general', script-related configuration values.

    Attributes:
        silent (bool):
            Run script in silent mode.
            Do not interact with user to enable full automation.
            (Default = False).
        ppprocedure (str):
            'Post Processing' stored procedure to be executed
            after prices have been loaded.
        ppdb (str):
            Database in which the ppprocedure is stored.
            Required when using `ppprocedure`.
        do_pp (bool):
            Execute post processing.

    """

    silent: bool
    ppprocedure: str
    ppdb: str
    do_pp: bool

    def __post_init__(self):
        """Validate and enricht configuration."""

        if self.ppprocedure is not None and self.ppdb is not None:
            self.do_pp = True
        elif self.ppprocedure is None and self.ppdb is None:
            self.do_pp = False

        if self.silent:
            if self.ppprocedure is not None and self.ppdb is None:
                sys.tracebacklimit = 0
                try:
                    raise ConfigError(
                        f"{self.ppprocedure} provided for post processing, but no `ppdb`.\n"
                        f"When using `ppprocedure`, `ppdb` must be provided as well.\n"
                        f"Exiting script...\n"
                    )
                except ConfigError:
                    self.do_pp = False
            elif self.ppprocedure is None and self.ppdb is not None:
                sys.tracebacklimit = 0
                try:
                    raise ConfigError(
                        f"{self.ppdb} provided for post processing, but no procedure to execute.\n"
                        f"When using `ppdb`, `ppprocedure` must be provided as well.\n"
                        f"Skipping post processing."
                    )
                except ConfigError:
                    self.do_pp = False

@dataclass
class ConnectionConfig:
    """Class to store MariaDB connection configuration values.

    Attributes:
        host (str):
            MariaDB host name or IP-address.
        port (int):
            MariaDB port
            (Default = 3306).
        user (str):
            MariaDB username
            (Default = `current system user`).
        pwd (str):
            MariaDB password.
    Important:
        When using `silent`, `pwd` must be provided in `config.ini` or cli.

    """

    host: str
    port: int
    user: str
    pwd: str
    silent: InitVar[bool]

    def __post_init__(self, silent):
        """Validate and enricht configuration."""

        if self.host is None:
            sys.tracebacklimit = 0
            raise ConfigError("MariaDB Server host address is mandatory.\nExiting script...\n")

        if self.user is None:
            # If no username was provided through cli or `config.ini`
            default_user = getpass.getuser().title()
            if silent:
                # AND IF `--silent` mode is active, use current system username
                self.user = default_user
            else:
                # ELSE, get username from user
                helpers.print_headerline("-", True)
                self.user = get_username(self, default_user)

        if self.pwd is None:
            if silent:
                sys.tracebacklimit = 0
                raise ConfigError("When using `silent` mode, "
                    "a password must be provided in `config.ini` or cli.\nExiting script...\n")
            self.pwd = get_pwd()

@dataclass
class GnuCashConfig:
    """Class to store GnuCash configuration values

    Attributes:
        database (str):
            GnuCash database name
            (Default = gnucash).
        currency (str):
            GnuCash book default/base currency
            (Default = EUR).

    """

    database: str
    currency: str

@dataclass
class DataConfig:
    """Class to store Data processing configuration values

    Attributes:
        to_mdb (bool):
            Load prices to MariaDB
            (Default = False).
        to_csv (bool):
            Save prices to csv
            (Default = False).
        output_path (str):
            Output path to store prices in csv
            (Default = consolidated_prices.csv).
        overwrite_csv (bool):
            Overwrite csv if it already exists
            (Default = False).

    """

    to_mdb: bool
    to_csv: bool
    output_path: str
    overwrite_csv: bool

@dataclass
class YahooFinanceConfig:
    """Class to store Yahoo!Finance configuration values

    Attributes:
        period (str):
            | Data period to download
              (Default = auto).
            | Choices: auto, 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max.
            | 'auto' will determine start date based on last available price date in `database`.
        start_date (date):
            If not using period: download start date string (YYYY-MM-DD).
        end_date (date):
            If not using period: download end date string (YYYY-MM-DD)
            (Default = `today`).

    Important:
        Either use `period` or use `start_date` and `end_date`.

    """

    period: str
    start_date: date
    end_date: date

class ConfigError(ValueError):
    """Raised when a configuration variable is not defined correctly."""

def process_config():
    """Main function to process configuration variables.

    Returns:
        A 'CustomConfig' `dataclass` object,
        containing a set of configuration variables

    """

    cli_args = parse_args()
    config_ini = parse_config(cli_args['config'])
    # Set config_defaults as ultimate fallback
    config_defaults = {
        'silent': False,
        'ppprocedure': None,
        'ppdb': None,
        'do_pp': False,
        'host': None,
        'port': 3306,
        'user': None,
        'pwd': None,
        'database': 'gnucash',
        'currency': 'EUR',
        'to_mdb': False,
        'to_csv': False,
        'output_path': 'consolidated_prices.csv',
        'overwrite_csv': False,
        'period': 'auto',
        'start_date': None,
        'end_date': date.today()
    }

    # Combine parsed Command Line Arguments, with `config.ini` into a ChainMap
    # The ChainMap will use cli_args, if provided.
    # If no parsed argument is provided for the key, it will use values from `config.ini`
    # If no cli args and no value from `config.ini`, it will use hardcoded defaults
    config_cm = ChainMap(cli_args, config_ini, config_defaults)

    # Initialize config objects per section from defaults ChainMap,

    # General Section
    general = GeneralConfig(
        config_cm['silent'],
        config_cm['ppprocedure'],
        config_cm['ppdb'],
        config_cm['do_pp']
    )

    # MariaDB Server Section
    conn = ConnectionConfig(
        config_cm['host'],
        config_cm['port'],
        config_cm['user'],
        config_cm['pwd'],
        general.silent
    )

    # GnuCash Section
    gnucash = GnuCashConfig(
        config_cm['database'],
        config_cm['currency']
    )

    # Data Section
    data = DataConfig(
        config_cm['to_mdb'],
        config_cm['to_csv'],
        config_cm['output_path'],
        config_cm['overwrite_csv']
    )

    # Yahoo!Finance Section
    yahoo_finance = YahooFinanceConfig(
        config_cm['period'],
        config_cm['start_date'],
        config_cm['end_date']
    )

    
    # Collect input from user if not running in `silent` mode
    if not general.silent:
        helpers.print_headerline("-", True)
        data.to_mdb = get_bool(
            f"Load prices to '{gnucash.database}'?"
            f" ['Enter' = {data.to_mdb}] ",
            data.to_mdb if isinstance(data.to_mdb, bool) else 'force'
        )

        data.to_csv = get_bool(
            f"Save prices to: {data.output_path}?"
            f" ['Enter' = {data.to_csv}] ",
            data.to_csv if isinstance(data.to_csv, bool) else 'force'
        )

        if general.ppprocedure is not None and general.ppdb is not None:
            general.do_pp = get_bool(
                f"Execute stored procedure '{general.ppprocedure}' @ '{general.ppdb}'?"
                f" ['Enter' = {data.to_mdb}] ",
                data.to_mdb
            )
        elif general.ppprocedure is not None and general.ppdb is None:
            print(
                f"You've provided {general.ppprocedure} for post processing, "
                f"but no [required] `ppdb`.\n"
                f"Skipping post processing..."
            )
            general.do_pp = False
        elif general.ppprocedure is None and general.ppdb is not None:
            print(
                f"You've provided {general.ppdb} for post processing, "
                f"but no [required] `ppprocedure`.\n"
                f"Skipping post processing..."
            )
            general.do_pp = False

        # If user chose to write prices to csv, delete pre-existing csv-file, if present
        if data.to_csv:
            data.to_csv = delete_csv(data.output_path, data.overwrite_csv)

    return general, conn, gnucash, data, yahoo_finance

def parse_args() -> dict:
    """Parse Command Line Arguments.

    Returns:
        Parsed arguments from Command Line as a dictionary.

    Note:
        To enable `config.ini`, ArgumentParser defaults should be removed
        OR set to `None` when using `action='store_true'`.
        Otherwise ArgumentParser will always provide a value
        (either from cli or defined default
        OR from default `False` i.c.o. `action='store_true'`)
        , which will take precedence over `config.ini` values

    """

    class CustomFormatter(
        argparse.ArgumentDefaultsHelpFormatter,
        argparse.RawDescriptionHelpFormatter
    ):
        """Create a new argparse formatter to combine
        ArgumentDefaultsHelpFormatter and RawDescriptionHelpFormatter

        Use multple inheritance to combine ability to:
        assume correct formatting / avoid line-wrapping description (RawDescriptionHelpFormatter)
        and
        add deaults value to each of the argument help messages

        """

    prog_descr = ("1. Retrieves commodities from GnuCash."
                "\n2. Downloads prices for each commodity from Yahoo!Finance."
                "\n   (using the yfinance Python module."
                "\n3a. Save prices to a pre-formatted csv for easy manual import."
                "\n    and/or"
                "\n3b. Load prices to GnuCash price table directly.")
    parser = argparse.ArgumentParser(description = prog_descr, formatter_class = CustomFormatter)
    parser.add_argument(
        '--silent',
        action = 'store_true',
        default = None,
        help = "Run script in silent mode. Do not interact with user to enable full automation."
    )
    parser.add_argument(
        '--config',
        default = 'config.ini',
        help = "Define an alternate 'config.ini' to use."
    )
    parser.add_argument(
        '--ppprocedure',
        help = "'Post Processing' stored procedure to be executed after prices have been loaded."
    )
    parser.add_argument(
        '--ppdb',
        help = "Database in which the ppprocedure is stored. Required when using `ppprocedure`."
    )

    # MariaDB server Options Group
    mdb_server_group = parser.add_argument_group('MariaDB server options')
    mdb_server_group.add_argument(
        '--host',
        help = "MariaDB host name or IP-address."
    )
    mdb_server_group.add_argument(
        '--port',
        help = "MariaDB port."
    )
    mdb_server_group.add_argument(
        '-u', '--user',
        help = "MariaDB username."
    )
    mdb_server_group.add_argument(
        '--pwd',
        help = "MariaDB password. " +
            "When using `--silent`, must be provided in `config.ini` or cli."
    )


    # GnuCash Options Group
    gnucash_group = parser.add_argument_group('GnuCash options')
    gnucash_group.add_argument(
        '-d', '--database',
        help = "GnuCash database name."
    )
    gnucash_group.add_argument(
        '-c', '--currency',
        help = "GnuCash book default/base currency."
    )

    # Data Options Group
    data_group = parser.add_argument_group('Data options')
    data_group.add_argument(
        '--to-mdb',
        action = 'store_true',
        default = None,
        help = "Load prices to MariaDB."
    )
    data_group.add_argument(
        '--to-csv',
        action = 'store_true',
        default = None,
        help = "Save prices to csv."
    )
    data_group.add_argument(
        '-o', '--output-path',
        help = "Output path to store prices in csv"
    )
    data_group.add_argument(
        '--overwrite-csv',
        action = 'store_true',
        default = None,
        help = "Overwrite csv if it already exists."
    )

    # Yahoo!Finance Options group
    yf_group = parser.add_argument_group('Yahoo!Finance options')
    yf_group.add_argument(
        '-p', '--period',
        choices = ['auto', '1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max'],
        help = "Data period to download (either use `period` or use `start_date` and `end_date`." +
            "'auto' will determine start date based on last available price date in `database`."
    )
    yf_group.add_argument('-s', '--start-date',
        help = "If not using period: download start date string (YYYY-MM-DD)."
    )
    yf_group.add_argument(
        '-e', '--end-date',
        default = date.today(),
        help = "If not using period: download end date string (YYYY-MM-DD)."
    )

    # Return parsed arguments as a dictionary
    return {k: v for k,v in vars(parser.parse_args()).items() if v is not None}

def parse_config(ini_file: str) -> dict:
    """Parse Configuration Arguments.

    Args:
        ini_file: name of the `'config'.ini` file.

    Returns:
        Parsed configuration from `config.ini` as a dictionary.

    """

    # Collect argument defaults from 'config.ini'
    config = configparser.ConfigParser()
    config.read(ini_file)

    # Add each Section's config entries to a single dictionary, excluding Section headers
    config_ini = {}
    for section in config.keys():
        config_ini.update(dict(config.items(section)))

    # Convert boolean values from str to bool
    for key, value in config_ini.items():
        if value.lower() == 'true' or value.lower() == 'false':
            config_ini[key] = value.lower() == 'true'

    return config_ini

def get_username(connection_cfg: ConnectionConfig, default_user: str) -> str:
    """Get MariaDB username from user. Defaults to current system user.

    Args:
        connection_cfg: Connection configuration variables.
        default_user: Default username to use if no input by user.

    Returns:
        Username to log in to MariaDB, using `connection`.

    """

    print(
        f"Enter a username and password to connect to: "
        f"MariaDB://{connection_cfg.host}:{connection_cfg.port}"
    )
    return input(
        f"Provide username or hit 'Enter' to use default "
        f"({default_user}): ") or default_user

def get_pwd() -> str:
    """Get MariaDB password from user.

    Returns:
        Password to log in to MariaDB.

    """

    pwd = getpass.getpass()
    while not pwd:
        pwd = getpass.getpass('Password cannot be empty. Please enter a Password: ')
    return pwd

def get_bool(prompt: str, default: str | bool) -> bool:
    """Helper function to prompt user for confirmation of an action.

    Args:
        prompt: The action to be confirmed by the user.
        default: default return value, if no input is given by the user \
        (i.e. user hits 'Enter' upon prompt).

    Returns:
        True if action is to be executed by the script.
        False if action should not be executed by the script.

    """

    valid_defaults = ('force', True, False)
    if default not in valid_defaults:
        raise ValueError(f"Prompt default must be one of {valid_defaults}.")

    while True:
        valid_responses = {}

        valid_pos_resp = ['y', 'yes', 't', 'true']
        for i in valid_pos_resp:
            valid_responses.update({i:True})

        valid_neg_resp = ['n', 'no', 'f', 'false']
        for i in valid_neg_resp:
            valid_responses.update({i:False})

        try:
            if isinstance(default, bool):
                # Add `default` to `valid_responses`,
                # so user can hit 'Enter'/provide empty response to return `default`
                valid_responses[""] = default
            # If `default` = 'force', "" will not be added to `valid_responses`
            # therefor the try will fail without an input != ""
            response = valid_responses[input(prompt).lower()]
            print(f"-> {response}")
            return response
        except KeyError:
            print(f"Invalid input. Please enter: {valid_pos_resp} OR {valid_neg_resp}")

def delete_csv(output_path: str, overwrite_csv: bool) -> bool:
    """Delete pre-existing file @ <output_path>, if present.

    Args:
        output_path (str): Output path to store prices in csv
        overwrite_csv (bool): Preference to overwrite csv

    Returns:
        (Updated) to_csv configuration variable.

    """

    if os.path.exists(output_path):
        overwrite_csv = get_bool(
            f"{output_path} already exists."
            f" Do you want to overwrite? ['Enter' = {overwrite_csv}] ",
            overwrite_csv if isinstance(overwrite_csv, bool) else 'force'
        )
        if overwrite_csv:
            print(f"Deleting {output_path}...")
            os.remove(output_path)
            to_csv = True
        else:
            to_csv = False
    else:
        print(f"{output_path} does not exist / will be created.")
        to_csv = True

    return to_csv

def _print_cfg(cfg: object) -> None:
    """Print key/value pairs from cfg object.

    Args:
        cfg (object): 'CustomConfig' `dataclass` object of which key/value pairs will be printed.

    """

    helpers.print_headerline("-", True)
    print(type(cfg).__name__)
    helpers.print_headerline("-", False)
    for field in fields(cfg):
        print(f"{field.name + ':': <15} {getattr(cfg, field.name)}")

if __name__ == '__main__':
    general_cfg, conn_cfg, gnucash_cfg, data_cfg, yf_cfg = process_config()
    _print_cfg(general_cfg)
    _print_cfg(conn_cfg)
    _print_cfg(gnucash_cfg)
    _print_cfg(data_cfg)
    _print_cfg(yf_cfg)
