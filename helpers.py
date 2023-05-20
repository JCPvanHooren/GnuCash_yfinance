"""Helper Classes & Functions used across multiple modules

.. _Google Python Style Guide:
   http://google.github.io/styleguide/pyguide.html

"""

import argparse
import configparser
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
    """Store processed arguments from cli and defaults.ini"""
    
    def __init__(self):
        """Process arguments from cli and defaults.ini
        
        1. Parse cli Arguments, including default assertion as per ArgumentParser.
        2. Collect default Arguments from `defaults.ini`
        3. Set final Arguments in order of precedence:
            | <1> Arguments provided on cli
            | <2> If not defined on cli: default provided as per ArgumentParser
            | <3> If not defined in ArgumentParser: from `defaults.ini`
        
        Note:
            To enable defaults.ini, ArgumentParser defaults should be removed. Otherwise ArgumentParser will always provide a value (either from cli or defined default), which will take precedence over `defaults.ini` values
        
        """
        
        parsed_args = _parse_args()
        
        
        # Convert parsed arguments to a dictionary
        cli_args = {k: v for k,v in vars(parsed_args).items() if v is not None}
        
        # Collect argument defaults from 'defaults.ini'
        config = configparser.ConfigParser()
        config.read('defaults.ini')
        
        # Add each Section's config entries to a single dictionary, excluding Section headers
        defaults_ini = {}
        for section in config.sections():
            defaults_ini.update(config._sections[section])
        
        # Combine parsed Command Line Arguments, with 'defaults.ini' into a ChainMap
        # The ChainMap will use cli_args, if provided. If no parsed argument is provided, it will use values from defaults.ini
        defaults_cm = ChainMap(cli_args, defaults_ini)
        
        # Initialize properties from defaults ChainMap
        
        # MariaDB server options
        self._host = defaults_cm['host']
        self._port = defaults_cm['port']
        self._database = defaults_cm['database']
        
        # GnuCash options
        self._currency = defaults_cm['currency']
        
        # Data options
        self._output_path = defaults_cm['output_path']
        self._period = defaults_cm['period']
        self._start_date = defaults_cm['start_date'] if 'start_date' in defaults_cm else None
        self._end_date = defaults_cm['end_date']
    
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
    def currency(self) -> str:
        """GnuCash book default/base currency"""
        return self._currency
    
    @property
    def output_path(self) -> str:
        """Output path to store prices in csv"""
        return self._output_path
    
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
    
def _parse_args() -> argparse.ArgumentParser:
    """Parse Command Line Arguments.
    
    Returns:
        Parsed arguments from Command Line.
    
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
    
    mdb_server_group = parser.add_argument_group('MariaDB server options')
    mdb_server_group.add_argument('--host', help="MariaDB host name or IP-address")
    mdb_server_group.add_argument('--port', help="MariaDB port")
    mdb_server_group.add_argument('-d', '--database', help="GnuCash database name")
    
    gnucash_group = parser.add_argument_group('GnuCash options')
    gnucash_group.add_argument('-c', '--currency', help="GnuCash book default/base currency")
    
    data_group = parser.add_argument_group('Data options')
    data_group.add_argument('-o', '--output-path', help="Output path to store prices in csv")
    data_group.add_argument('-p', '--period', default = 'auto',
                            choices = ['auto', '1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max'],
                            help="Data period to download (either use period parameter or use start and end). 'auto' will determine start date based on last available price date")
    data_group.add_argument('-s', '--start-date', help="If not using period - Download start date string (YYYY-MM-DD)")
    data_group.add_argument('-e', '--end-date', default = date.today(), help="If not using period - Download end date string (YYYY-MM-DD)")
    return parser.parse_args()