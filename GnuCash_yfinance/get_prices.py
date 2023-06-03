"""Get commodity prices from Yahoo!Finance
and save them to preformatted csv
and/or load them to GnuCash @ MariaDB.

1. Retrieves commodities from GnuCash.
2. Downloads prices for each commodity from Yahoo!Finance (using the yfinance Python module.
3. Save prices to a pre-formatted csv for easy manual import
4. and/or Load prices to GnuCash `prices` table.

Note:
    All options can have a default value by adding the 'long' key in `config.ini`.

General options:
    -h, --help
        Show this help message and exit.
    --silent
        Run script in silent mode.
        Do not interact with user to enable full automation.
        (Default = False)
    --config
        Define an alternate `config.ini` to use.
        (Default = `config.ini`)
    --ppprocedure
        'Post Processing' stored procedure to be executed
        after prices have been loaded.
    --ppdb
        Database in which the ppprocedure is stored.
        Required when using `ppprocedure`.

MariaDB server options:
    --host HOST
        MariaDB host name or IP-address.
    --port PORT
        MariaDB port
        (Default = 3306).
    -u USERNAME, --user USERNAME
        MariaDB username
        (Default = `current system user`).
    --pwd
        MariaDB password.

Important:
    When using `silent`, `pwd` must be provided in `config.ini` or cli.

GnuCash options:
    -d DATABASE, --database DATABASE
        GnuCash database name
            (Default = gnucash).
    -c CURRENCY, --currency CURRENCY
        GnuCash book default/base currency
        (Default = EUR).

Data options:
    --to-mdb
        Load prices to MariaDB
        (Default = False).
    --to-csv
        Save prices to csv
        (Default = False).
    -o OUTPUT_PATH, --output-path OUTPUT_PATH
        Output path to store prices in csv
        (Default = consolidated_prices.csv).
    --overwrite_csv
        Overwrite csv if it already exists
        (Default = False).

Yahoo!Finance options:
    -p PERIOD, --period PERIOD
        | Data period to download (Default = auto).
            | Data period to download
              (Default = auto).
            | Choices: auto, 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max.
            | 'auto' will determine start date based on last available price date in `database`.
    -s START_DATE, --start-date START_DATE
        If not using period: Download start date string (YYYY-MM-DD).
    -e END_DATE, --end-date END_DATE
        If not using period: Download end date string (YYYY-MM-DD)
        (Default = `today`).

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
import config
import mdb
import df

def main() -> None:
    """The main module to download commodity prices from Yahoo!Finance \
    and store them in csv @ <output-path> and/or GnuCash @ MariaDB

    """

    general_cfg, conn_cfg, gnucash_cfg, data_cfg, yf_cfg = config.process_config()

    if not general_cfg.silent:
        # Collect user input
        data_cfg.to_mdb = get_bool(
            f"Load prices to '{gnucash_cfg.database}'?"
            f" ['Enter' = {data_cfg.to_mdb}] ",
            data_cfg.to_mdb if isinstance(data_cfg.to_mdb, bool) else 'force'
        )

        data_cfg.to_csv = get_bool(
            f"Save prices to: {data_cfg.output_path}?"
            f" ['Enter' = {data_cfg.to_csv}] ",
            data_cfg.to_csv if isinstance(data_cfg.to_csv, bool) else 'force'
        )

        execute_ppprocedure = get_bool(
            f"Execute stored procedure '{general_cfg.ppprocedure}' @ '{general_cfg.ppdb}'?"
            f" ['Enter' = {general_cfg.ppprocedure is not None}] ",
            general_cfg.ppprocedure is not None
        )

        # If user chose to write prices to csv, delete pre-existing csv-file, if present
        if data_cfg.to_csv:
            delete_csv(data_cfg.output_path, data_cfg.overwrite_csv)

    # Check presence of required config values
    if general_cfg.silent and conn_cfg.pwd is None:
        print("Silent mode activated, but no password provided.")
        print("When activating 'silent' mode, "
            "always provide a GnuCash MariaDB password through cli or 'config.ini'")
        sys.exit("Exiting script...")

    gnucash_engine = mdb.create_engine(conn_cfg, gnucash_cfg.database)
    commodities = mdb.get_commodities(gnucash_engine)

    # Process each commodity
    for commodity in commodities:
        helpers.print_headerline("-", True)
        print(
            f"Full Name: {commodity.fullname}\n"
            f"Mnemonic: {commodity.mnemonic}\n"
            f"Namespace: {commodity.namespace}\n"
            f"Last Price Date: {commodity.last_price_date}",
            end = ''
        )
        helpers.print_headerline("-", True)

        # create DataFrame that contains commodity prices
        comm_df = df.CommodityDataFrame(commodity, gnucash_cfg.currency, yf_cfg)

        if not comm_df.full_df.empty:
            # Print dataframe
            print(comm_df.stdout_df)

            if data_cfg.to_csv:
                # Write dataframe to CSV
                print(f"\nWriting to {data_cfg.output_path}... ", end = '')
                comm_df.full_df.to_csv(
                    data_cfg.output_path,
                    mode = 'a',
                    header = not os.path.exists(data_cfg.output_path)
                )
                print("ADDED")

            if data_cfg.to_mdb:
                # Load to GnuCash @ MariaDB through SQL
                print("\nLoading to GnuCash @ MariaDB through SQL...")
                comm_df.sql_df.to_sql(
                    name = 'prices',
                    con = gnucash_engine,
                    if_exists = 'append',
                    index = True
                )
    # Run 'post processing' stored procedure, if provided
    if (
        general_cfg.ppprocedure is not None
        and execute_ppprocedure is not False
    ):
        if general_cfg.ppdb is None:
            print(
                f"Post processing database not provided.\n"
                f"Cannot execute '{general_cfg.ppprocedure}'.")
            sys.exit("Exiting script...")
        else:
            gnu_inv_engine = mdb.create_engine(conn_cfg, general_cfg.ppdb)
            mdb.execute_procedure(general_cfg.ppprocedure, gnu_inv_engine)

def delete_csv(output_path: str, overwrite_csv: bool) -> None:
    """Delete pre-existing file @ <output_path>, if present.

    Args:
        output_path (str): Output path to store prices in csv
        overwrite_csv (bool): Preference to overwrite csv

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
        else:
            sys.exit("Exiting script...")
    else:
        print(f"{output_path} does not exist / will be created.")

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

if __name__ == '__main__':
    main()
