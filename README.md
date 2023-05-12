# GnuCash_yfinance
 
## Background

For a while I've used [sdementen/piecash](https://github.com/sdementen/piecash) to download commodity prices and load them to GnuCash. Unfortunately this repo seems to have gone stale and recently stopped working for me. The gnucash part of the module works fine, but collecting prices from Yahoo!Finance always has been the fragile part and ultimately stopped working.

Because I only have a simple need and I'm not a professional, I decided to create my own script and share it for whoever thinks this may help them.
Any suggestions to improve are also welcome.

### My needs:
1. Download commodity prices from the internet
2. Load these commodity prices to GnuCash
3. With as little effort as possible

## Overview
The script does the following:
1. Retrieve commodities from GnuCash (using [ranaroussi/yfinance](https://github.com/ranaroussi/yfinance))
2. Download prices for each commodity from Yahoo!Finance
3. Save prices to a pre-formatted csv for easy manual import and/or Load prices to GnuCash price table directly

## Options

### defaults.ini

The `defaults.ini` file can be used to customize default options, preventing the need to provide arguments in the command line. This will help to set default values that are used most regularly, while allowing for the default value to still be overwritten by providing options in the command line.

### MariaDB server options:

|Short|Long|Description|Default|
|-|-|-|-|
||--host|MariaDB host name or IP-address |192.168.1.x|
||--port|MariaDB port|3306|
|-db|--database|GnuCash database name|gnucash|

### GnuCash options:
|Short|Long|Description|Default|
|-|-|-|-|
|-c|--currency|GnuCash book default/base currency|EUR|

### Data options:
|Short|Long|Description|Default|Options|
|-|-|-|-|-|
|-o|--output-path|Output path to store prices in csv|./consolidated_prices.csv||
|-p|--period|Data period to download (either use period parameter or use start and end). 'auto' will determine start date based on last available price date|auto|auto, 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max|
|-s|--start|If not using period - Download start date string (YYYY-MM-DD)||
|-e|--end|If not using period - Download end date string (YYYY-MM-DD)|_'today'_

## Modules
|Filename|Description|
|-|-|
|get_prices.py|Main module|
|helpers.py|Helper functions used across multiple modules|
|mdb.py|'MDB' Class<br/>to work with GnuCash @ MariaDB,<br/>using [SQLAlchemy](https://www.sqlalchemy.org/)|
|df.py|'DF' Class <br/>to create & store [Pandas](https://pandas.pydata.org/) DataFrames per commodity,<br/> retrieved from [Yahoo!Finance](https://finance.yahoo.com/),<br/>using [ranaroussi/yfinance](https://github.com/ranaroussi/yfinance)|
