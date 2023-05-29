"""Get commodity prices from Yahoo!Finance
and save them to preformatted csv
and/or load them to GnuCash @ MariaDB.

1. Retrieves commodities from GnuCash.
2. Downloads prices for each commodity from Yahoo!Finance (using the yfinance Python module.
3. Save prices to a pre-formatted csv for easy manual import
4. and/or Load prices to GnuCash `prices` table.

Note:
    All options can have a default value by adding the 'long' key in `config.ini`.

options:
    -h, --help  Show this help message and exit.
    --silent    Run script in silent mode. \
        Do not interact with user to enable full automation. (default: False)
    --config    Define an alternate `config.ini` to use. (default: `config.ini`)

MariaDB server options:
    --host HOST
        MariaDB host name or IP-address
    --port PORT
        MariaDB port (default: 3306)
    -d DATABASE, --database DATABASE
        GnuCash database name (default: gnucash)
    -u USERNAME, --user USERNAME
        GnuCash MariaDB username (default: current system username)
    --pwd
        GnuCash MariaDB password. When using `--silent`, must be provided in `config.ini` or cli.

GnuCash options:
    -c CURRENCY, --currency CURRENCY
        GnuCash book default/base currency (default: EUR)

Data options:
    --to-mdb
        Load prices to MariaDB (default: False)
    --to-csv
        Save prices to csv (default: False)
    -o OUTPUT_PATH, --output-path OUTPUT_PATH
        Output path to store prices in csv (default: 'consolidated_prices.csv')
    --overwrite_csv
        Overwrite csv if it already exists (default: False)

Yahoo!Finance options:
    -p PERIOD, --period PERIOD
        Data period to download (either use period parameter or use start and end). \
            'auto' will determine start date based on last available price date (default: auto)
    -s START_DATE, --start-date START_DATE
        If not using period: Download start date string (YYYY-MM-DD) (default: None)
    -e END_DATE, --end-date END_DATE
        If not using period: Download end date string (YYYY-MM-DD) (default: `today`)

.. _Google Python Style Guide:
   http://google.github.io/styleguide/pyguide.html

"""

__author__ = "Joost van Hooren"
__date__ = "May 2023"
__license__ = "GPL"
__credits__ = (
    "ranaroussi, for creating and maintaining yfinance (https://github.com/ranaroussi/yfinance)"
)

import sys
import os

import helpers
from mdb import MDB
from df import DF

args = None # pylint: disable-msg=C0103

def main() -> None:
    """The main module to download commodity prices from Yahoo!Finance \
    and store them in csv @ <output-path> and/or GnuCash @ MariaDB

    """

    global args # pylint: disable-msg=W0603
    args = helpers.Args()

    if not args.silent:
        args.to_mdb = get_bool(
            f"Load prices to: MariaDB://{args.host}:{args.port}/{args.database}?"
            f" ['Enter' = {args.to_mdb}] ",
            args.to_mdb if isinstance(args.to_mdb, bool) else 'force'
        )

        args.to_csv = get_bool(
            f"Save prices to: {args.output_path}?"
            f" ['Enter' = {args.to_csv}] ",
            args.to_csv if isinstance(args.to_csv, bool) else 'force'
        )

        # If user chose to write prices to csv, delete pre-existing csv-file, if present
        if args.to_csv:
            delete_csv()

    # GnuCash @ MariaDB
    if args.silent and args.pwd is None:
        print("Silent mode activated, but no password provided.")
        print("When activating 'silent' mode, "
            "always provide a GnuCash MariaDB password through cli or 'config.ini'")
        sys.exit("Exiting script...")
    else:
        mdb = MDB(args)

    # Process each commodity
    for commodity in mdb.commodities:
        helpers.print_headerline("-", True)
        print(
            f"Full Name: {commodity.fullname}\n"
            f"Mnemonic: {commodity.mnemonic}\n"
            f"Namespace: {commodity.namespace}\n"
            f"Last Price Date: {commodity.last_price_date}",
            end = ''
        )
        helpers.print_headerline("-", True)

        # create DF object, containing relevant DataFrames
        df = DF(commodity, args) # pylint: disable-msg=C0103

        if not df.full_df.empty:
            # Print dataframe
            print(df.stdout_df)

            if args.to_csv:
                # Write dataframe to CSV
                print(f"\nWriting to {args.output_path}... ", end = '')
                df.full_df.to_csv(
                    args.output_path,
                    mode = 'a',
                    header = not os.path.exists(args.output_path)
                )
                print("ADDED")

            if args.to_mdb:
                # Load to GnuCash @ MariaDB through SQL
                print("\nLoading to GnuCash @ MariaDB through SQL...")
                df.sql_df.to_sql(
                    name = 'prices',
                    con = mdb.engine,
                    if_exists = 'append',
                    index = True
                )

def delete_csv() -> None:
    """Delete pre-existing file @ <output_path>, if present."""

    if os.path.exists(args.output_path):
        args.overwrite_csv = get_bool(
            f"{args.output_path} already exists."
            f" Do you want to overwrite? ['Enter' = {args.overwrite_csv}] ",
            args.overwrite_csv if isinstance(args.overwrite_csv, bool) else 'force'
        )
        if args.overwrite_csv:
            print(f"Deleting {args.output_path}...")
            os.remove(args.output_path)
        else:
            sys.exit("Exiting script...")
    else:
        print(f"{args.output_path} does not exist / will be created.")

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
            return valid_responses[input(prompt).lower()]
        except KeyError:
            print(f"Invalid input. Please enter: {valid_pos_resp} OR {valid_neg_resp}")

if __name__ == '__main__':
    main()
