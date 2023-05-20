"""Get commodity prices from Yahoo!Finance and save them to preformatted csv and/or load them to GnuCash @ MariaDB.

1. Retrieves commodities from GnuCash.
2. Downloads prices for each commodity from Yahoo!Finance (using the yfinance Python module.
3. Save prices to a pre-formatted csv for easy manual import
4. and/or Load prices to GnuCash `prices` table

options:
  -h, --help            show this help message and exit

MariaDB server options:
  --host HOST
        MariaDB host name or IP-address (default: None)
  --port PORT
        MariaDB port (default: None)

  -d DATABASE, --database DATABASE
        GnuCash database name (default: None)

GnuCash options:
  -c CURRENCY, --currency CURRENCY
                        GnuCash book default/base currency (default: None)

Data options:
  -o OUTPUT_PATH, --output-path OUTPUT_PATH
                        Output path to store prices in csv (default: None)
  -p PERIOD, --period PERIOD
                        Data period to download (either use period parameter or use start and end). 'auto' will determine start date based on last available price date (default: auto)
  -s START_DATE, --start-date START_DATE
                        If not using period - Download start date string (YYYY-MM-DD) (default: None)
  -e END_DATE, --end-date
                        END_DATE If not using period - Download end date string (YYYY-MM-DD) (default: 'today')

.. _Google Python Style Guide:
   http://google.github.io/styleguide/pyguide.html

"""

__author__ = "Joost van Hooren"
__date__ = "May 2023"
__license__ = "GPL"
__credits__ = "ranaroussi, for creating and maintaining yfinance (https://github.com/ranaroussi/yfinance)"

import sys
import os

import helpers
from mdb import MDB
from df import DF

def main() -> None:
    """The main module to download commodity prices from Yahoo!Finance and store them in csv @ <output-path> and/or GnuCash @ MariaDB"""
    
    args = helpers.Args()
    to_mdb = get_bool(f"Load prices to: MariaDB://{args.host}:{args.port}/{args.database}? ['Enter' = True] ", False)
    to_csv = get_bool(f"Save prices to: {args.output_path}? ['Enter' = False] ", True)
    
    # If user chose to write prices to csv, delete pre-existing csv-file, if present 
    if to_csv:
        delete_csv(args.output_path)
    
    # GnuCash @ MariaDB
    mdb = MDB(args.host, args.port, args.database)

    # Process each commodity
    for commodity in mdb.commodities:
        helpers.print_headerline("-", True)
        print(f"Full Name: {commodity.fullname}\nMnemonic: {commodity.mnemonic}\nNamespace: {commodity.namespace}\nLast Price Date: {commodity.last_price_date}", end = '')
        helpers.print_headerline("-", True)
        
        # create DF object, containing relevant DataFrames
        df = DF(commodity, args.currency, args.start_date, args.end_date, args.period)
        
        if not df.full_df.empty:
            # Print dataframe
            print(df.stdout_df)
            
            if to_csv:
                # Write dataframe to CSV
                print(f"\nWriting to {args.output_path}... ", end = '')
                df.full_df.to_csv(args.output_path, mode = 'a', header = not os.path.exists(args.output_path))
                print("ADDED")
            
            if to_mdb:
                # Load to GnuCash @ MariaDB through SQL
                print("\nLoading to GnuCash @ MariaDB through SQL...")
                df.sql_df.to_sql(name = 'prices', con = mdb.engine, if_exists = 'append', index = True)

def delete_csv(output_path: str) -> None:
    """Delete pre-existing file @ <output_path>, if present.
    
    Args:
        output_path: Path where csv-file is to be written.
    
    """
    
    if os.path.exists(output_path):
        delete_choice = get_bool(f"{output_path} already exists. Do you want to overwrite? ['Enter' = True] ", True)
        if delete_choice:
            print(f"Deleting {output_path}...")
            os.remove(output_path)
        else:
            sys.exit("Exiting script...")
    else:
        print(f"{output_path} does not exist / will be created.")

def get_bool(prompt: str, default: str | bool) -> bool:
    """Helper function to prompt user for confirmation of an action.
    
    Args:
        prompt: The action to be confirmed by the user.
        default: default return value, if no input is given by the user (i.e. user hits 'Enter' upon prompt).
    
    Returns:
        True if action is to be executed by the script. False if action should not be executed by the script.
    
    """
    
    VALID_DEFAULTS = ('force', True, False)
    if default not in VALID_DEFAULTS:
        raise ValueError("Prompt default must be one of %r." % VALID_DEFAULTS)
    
    while True:
        valid_responses = {"y":True, "n":False}
        try:
            if default == 'force':
                return valid_responses[input(prompt).lower()]
            else:
                valid_responses[""] = default 
                return valid_responses[input(prompt).lower()]
        except KeyError:
            print("Invalid input please enter 'y'/'Y' (Yes) or 'n'/'N' (No)!")

if __name__ == '__main__':
    main()