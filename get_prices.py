import sys
import os

import helpers
from mdb import MDB
from df import DF

def delete_csv(output_path):
    # Delete CSV if present
    if os.path.exists(output_path):
        delete_choice = get_bool(f"{output_path} already exists. Do you want to overwrite? ['Enter' = True] ", True)
        if delete_choice:
            print(f"Deleting {output_path}...")
            os.remove(output_path)
        else:
            sys.exit("Exiting script...")
    else:
        print(f"{output_path} does not exist / will be created.")

def get_bool(prompt, default):
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

def main():
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

if __name__ == '__main__':
    main()