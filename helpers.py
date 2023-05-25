"""Helper Classes & Functions used across multiple modules

If run as main module (not imported): print Arguments

.. _Google Python Style Guide:
   http://google.github.io/styleguide/pyguide.html

"""

import argparse
import configparser
import getpass
from typing import Optional
from collections import ChainMap
from datetime import date

def print_headerline(char: str, leading_newline: Optional[bool] = False) -> None:
    """Print a headerline, optionally with a leading empty line
    
    Args:
        char: Character to be printed 64 times.
        leading_newline: Print an empty line before printing the headerline. Defaults to False.
    
    """
    
    if leading_newline:
        print()
    print(char * 64)

class Args:
    """Store processed arguments from cli and config.ini"""
    
    def __init__(self):
        """Process arguments from cli and config.ini
        
        1. Parse cli Arguments, including default assertion as per ArgumentParser.
        2. Collect default Arguments from `config.ini`
        3. Set final Arguments in order of precedence:
            | <1> Arguments provided on cli
            | <2> If not defined on cli: default provided as per ArgumentParser
            | <3> If not defined in ArgumentParser: from `config.ini`
        
        Note:
            All options can have a default set by adding the 'long' key in `config.ini`
        
        """
        
        self._cli_args = parse_args()
        self._config_ini = parse_config(self._cli_args['config'])
                
        # Set config_defaults dict to identify potential hardcoded defaults
        self._config_defaults = {
            'silent': False,
            'host': None,
            'port': 3306,
            'database': 'gnucash',
            'user': None,
            'pwd': None,
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
        # If no parsed argument is provided, it will use values from `config.ini`
        # If no cli args and no value from `config.ini`, it will use hardcoded defaults
        self._defaults_cm = ChainMap(self._cli_args, self._config_ini, self._config_defaults)
        
        # Initialize properties from defaults ChainMap,        
        for key, default_value in self._defaults_cm.items():
            exec(f"self._{key} = self._defaults_cm['{key}'] if '{key}' in self._defaults_cm else '{default_value}'")
        
        # If `--silent` mode is active and no username provided, use current system username
        if self.silent and self.user is None: self._user = getpass.getuser().title()
        
    @property
    def silent(self) -> bool:
        """Run script in silent mode (or not)"""
        return self._silent
    
    @property
    def host(self) -> str:
        """MariaDB host name or IP-address"""
        return self._host
    
    @property
    def port(self) -> int:
        """MariaDB port"""
        return self._port
    
    @property
    def database(self) -> str:
        """GnuCash database name"""
        return self._database
    
    @property
    def user(self) -> str:
        """GnuCash MariaDB username
        
        Default: current system username
        """
        return self._user
    
    @property
    def pwd(self) -> str:
        """GnuCash MariaDB password"""
        return self._pwd
    
    @property
    def currency(self) -> str:
        """GnuCash book default/base currency"""
        return self._currency
    
    @property
    def to_mdb(self) -> bool:
        """User choice to load prices to GnuCash @ MariaDB (or not). Defaults to False."""
        return self._to_mdb
    
    @to_mdb.setter
    def to_mdb(self, val: bool) -> None:
        self._to_mdb = val
    
    @property
    def to_csv(self) -> bool:
        """User choice to save prices to csv (or not). Defaults to False"""
        return self._to_csv
    
    @to_csv.setter
    def to_csv(self, val: bool) -> None:
        self._to_csv = val
    
    @property
    def output_path(self) -> str:
        """Output path to store prices in csv (or not). Defaults to False."""
        return self._output_path
    
    @property
    def overwrite_csv(self) -> bool:
        """User choice to overwrite csv or not
        
        Can only be set once, to avoid overwriting `True` when to_csv is provided through `config.ini`. Will block attempt to re-set if already pre-set.
        """
        return self._overwrite_csv
    
    @overwrite_csv.setter
    def overwrite_csv(self, val: bool) -> None:
        if self._overwrite_csv is None:
            self._overwrite_csv = val
        else:
            print(f"overwrite_csv already set to {self.overwrite_csv}. Ignoring request to set")
    
    @property
    def period(self) -> str:
        """Data period to download (either use period parameter or use start and end).
        
        Default: 'auto'
        
        Valid choices: 'auto', '1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max'
        'auto' will determine start date based on last available price date
        """
        return self._period
    
    @property
    def start_date(self) -> date:
        """If not using period - Download start date string (YYYY-MM-DD)"""
        return self._start_date
    
    @property
    def end_date(self) -> date:
        """If not using period - Download end date string (YYYY-MM-DD)
        
        Default: `today`
        """
        return self._end_date
    
def parse_args() -> dict:
    """Parse Command Line Arguments.
    
    Returns:
        Parsed arguments from Command Line as a dictionary.
    
    Note:
        To enable config.ini, ArgumentParser defaults should be removed OR set to `None` when using `action='store_true'`. Otherwise ArgumentParser will always provide a value (either from cli or defined default OR from default `False` i.c.o. `action='store_true'`), which will take precedence over `config.ini` values
        
    """
    
    class CustomFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter):
        pass
    
    prog_descr = ("1. Retrieves commodities from GnuCash."
                "\n2. Downloads prices for each commodity from Yahoo!Finance"
                "\n   (using the yfinance Python module."
                "\n3a. Save prices to a pre-formatted csv for easy manual import"
                "\n    and/or"
                "\n3b. Load prices to GnuCash price table directly")
    parser = argparse.ArgumentParser(description=prog_descr, formatter_class=CustomFormatter)
    parser.add_argument('--silent', action='store_true', default=None, help="Run script in silent mode. Do not interact with user to enable full automation.")
    parser.add_argument('--config', default='config.ini', help="Define an alternate 'config.ini' to use")
    
    # MariaDB server Options Group
    mdb_server_group = parser.add_argument_group('MariaDB server options')
    mdb_server_group.add_argument('--host', help="MariaDB host name or IP-address")
    mdb_server_group.add_argument('--port', help="MariaDB port")
    mdb_server_group.add_argument('-d', '--database', help="GnuCash database name")
    mdb_server_group.add_argument('-u', '--user', help="GnuCash MariaDB username")
    mdb_server_group.add_argument('--pwd', help="GnuCash MariaDB password. Must be provided in `config.ini` or cli when using `--silent`.")
    
    
    # GnuCash Options Group
    gnucash_group = parser.add_argument_group('GnuCash options')
    gnucash_group.add_argument('-c', '--currency', help="GnuCash book default/base currency")
    
    # Data Options Group
    data_group = parser.add_argument_group('Data options')
    data_group.add_argument('--to-mdb', action='store_true', default=None, help="Load prices to MariaDB")
    data_group.add_argument('--to-csv', action='store_true', default=None, help="Save prices to csv")
    data_group.add_argument('-o', '--output-path', help="Output path to store prices in csv")
    data_group.add_argument('--overwrite-csv', action='store_true', default=None, help="Overwrite csv if it already exists")
    
    # Yahoo!Finance Options group
    yf_group = parser.add_argument_group('Yahoo!Finance options')
    yf_group.add_argument('-p', '--period',
                            choices = ['auto', '1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max'],
                            help="Data period to download (either use period parameter or use start and end). 'auto' will determine start date based on last available price date")
    yf_group.add_argument('-s', '--start-date', help="If not using period: Download start date string (YYYY-MM-DD)")
    yf_group.add_argument('-e', '--end-date', default = date.today(), help="If not using period: Download end date string (YYYY-MM-DD)")
    
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
    for section in config.sections():
        config_ini.update(config._sections[section])
    
    # Convert boolean values from str to bool
    for key in config_ini:
        if config_ini[key].lower() == 'true' or config_ini[key].lower() == 'false':
            config_ini[key] = config_ini[key].lower() == 'true'
    
    return config_ini


if __name__ == '__main__':
    args = vars(Args())
    for arg, val in args.items():
        print(f"{arg}: {val}")