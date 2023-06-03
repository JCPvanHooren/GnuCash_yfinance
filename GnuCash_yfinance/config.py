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

import argparse
import configparser
import getpass
from collections import ChainMap
from datetime import date
from dataclasses import dataclass, fields

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

    """

    silent: bool
    ppprocedure: str
    ppdb: str

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
        An 'CustomConfig' `dataclass` object,
        containing a set of configuration variables

    """

    default_user = getpass.getuser().title()

    cli_args = parse_args()
    config_ini = parse_config(cli_args['config'])
    # Set config_defaults as ultimate fallback
    config_defaults = {
        'silent': False,
        'ppprocedure': None,
        'ppdb': None,
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
        config_cm['ppdb']
    )

    if general.ppprocedure is not None and general.ppdb is None:
        raise ConfigError("When using `ppprocedure`, `ppdb` must be provided.")

    # MariaDB Server Section
    conn = ConnectionConfig(
        config_cm['host'],
        config_cm['port'],
        config_cm['user'],
        config_cm['pwd']
    )

    if conn.host is None:
        raise ConfigError("MariaDB Server host address is mandatory.")

    if conn.user is None:
        # If no username was provided through cli or `config.ini`
        if general.silent:
            # AND IF `--silent` mode is active, use current system username
            conn.user = default_user
        else:
            # ELSE, get username from user
            conn.user = get_username(conn, default_user)

    if conn.pwd is None:
        if general.silent:
            raise ConfigError("When using `silent` mode, "
                "a password must be provided in `config.ini` or cli.")
        conn.pwd = get_pwd()

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
        f"\nEnter a username and password to connect to: "
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
