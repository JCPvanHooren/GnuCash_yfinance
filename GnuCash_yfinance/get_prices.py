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

    # Run 'post processing' stored procedure, if desired
    if general_cfg.do_pp:
        helpers.print_headerline("-", True)
        print()
        gnu_inv_engine = mdb.create_engine(conn_cfg, general_cfg.ppdb)
        print(f"Executing {general_cfg.ppprocedure} @ {general_cfg.ppdb}... ", end = '')
        mdb.execute_procedure(general_cfg.ppprocedure, gnu_inv_engine)
        print("DONE\n")

    helpers.print_headerline("=", True)
    print("ALL DONE. Script completed...")
    print()

if __name__ == '__main__':
    main()
