"""Manage Pandas DataFrames

.. _Google Python Style Guide:
   http://google.github.io/styleguide/pyguide.html

"""

from datetime import timedelta
from datetime import date
import uuid

import pandas

import helpers
import yfinance

class DF:
    """Manage Pandas Dataframes"""
    def __init__(self, commodity, _args: helpers.Args):
        """Initialize DF Class.

        1. Set commodity
        2. Set properties
        3. Get DataFrame from Yahoo!Finance for relevant commodity
        4. Create 'Full' DataFrame for GnuCash, \
        including both SQL-relevant and CSV-relevant columns and values.

        Args:
            commodity: GnuCash commodity
            _args: Processed arguments from cli and/or `config.ini`

        """

        self._commodity = commodity
        self._currency = _args.currency
        self._start_date = _args.start_date
        self._end_date = _args.end_date
        self._period = _args.period

        self._get_yf()
        self._set_full()

    @property
    def commodity(self):
        """GnuCash commodity"""
        return self._commodity

    @property
    def currency(self) -> str:
        """GnuCash book default/base currency"""
        return self._currency

    @property
    def start_date(self) -> date:
        """If not using period - Download start date string (YYYY-MM-DD)"""
        return self._start_date

    @property
    def end_date(self) -> date:
        """If not using period - Download end date string (YYYY-MM-DD). Defaults to `today`."""
        return self._end_date

    @property
    def period(self) -> str:
        """Data period to download (either use period parameter or use start and end).

        | Defaults to 'auto', which will determine start date based on last available price date.
        | Valid choices = 'auto', '1d', '5d', '1mo', '3mo', '6mo', \
        '1y', '2y', '5y', '10y', 'ytd', 'max'.
        """
        return self._period

    @property
    def yf_df(self) -> pandas.DataFrame:
        """Pandas DataFrame with Commodity Prices from Yahoo!Finance"""
        return self._yf_df

    @property
    def full_df(self) -> pandas.DataFrame:
        """Pandas DataFrame with Full dataset for GnuCash,
        including both SQL-relevant and CSV-relevant columns and values.
        """
        return self._full_df

    @property
    def stdout_df(self) -> pandas.DataFrame:
        """Pandas DataFrame with selected data to print to STDOUT"""
        return self.full_df[['Curr', 'Close']]

    @property
    def sql_df(self) -> pandas.DataFrame:
        """Pandas DataFrame with selected data for SQL Load to GnuCash `prices` table @ MariaDB"""
        return self.full_df[[
            'guid',
            'commodity_guid',
            'currency_guid',
            'source',
            'type',
            'value_num',
            'value_denom'
        ]]

    def _get_yf(self) -> None:
        """Get DataFrame from Yahoo!Finance for relevant commodity"""
        if self.commodity.namespace == 'CURRENCY':
            yf_symbol = self.commodity.mnemonic + self.currency + '=X'
        else:
            yf_symbol = self.commodity.mnemonic

        if self.start_date:
            self._yf_df = yfinance.Ticker(yf_symbol).history(
                start = self.start_date, end = self.end_date)
        else:
            if self.period == 'auto':
                start_date = self.commodity.last_price_date + timedelta(1)
                self._yf_df = yfinance.Ticker(yf_symbol).history(
                    start = start_date, end = self.end_date)
            else:
                self._yf_df = yfinance.Ticker(yf_symbol).history(self.period)

    def _set_full(self) -> None:
        """Create Full DataFrame by processing and enriching Yahoo!Finance DataFrame"""
        if (not self.yf_df.empty and self.commodity.mnemonic != self.currency):
            self._full_df = self.yf_df[['Close']].copy()
            self._full_df.index = self.full_df.index.tz_localize(None)
            self._full_df.index.name = 'date'
            self._full_df['Curr'] = self.currency
            self._full_df['Symbol'] = self.commodity.mnemonic
            self._full_df['Full_Name'] = self.commodity.fullname
            self._full_df['Namespace'] = self.commodity.namespace
            if self.commodity.namespace == 'CURRENCY':
                self._full_df['Close'] = self.full_df['Close'].round(decimals = 5)
            else:
                self._full_df['Close'] = self.full_df['Close'].round(decimals = 2)
            self._full_df['guid'] = [uuid.uuid4().hex for _ in range(len(self.full_df.index))]
            self._full_df['commodity_guid'] = self.commodity.guid
            self._full_df['currency_guid'] = self.commodity.currency_guid
            self._full_df['source'] = 'user:price'
            self._full_df['type'] = 'last'
            self._full_df['value_num'] = self.full_df['Close'] * self.commodity.value_denom
            self._full_df['value_denom'] = self.commodity.value_denom
        else:
            self._full_df = pandas.DataFrame()
