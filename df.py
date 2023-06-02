"""Manage Pandas DataFrames

.. _Google Python Style Guide:
   http://google.github.io/styleguide/pyguide.html

"""

from datetime import timedelta
from datetime import date
import uuid

import pandas
import yfinance

import config

class CommodityDataFrame:
    """Manage Pandas Dataframes"""
    def __init__(self, commodity, currency: str, data_cfg: config.DataConfig):
        """Initialize DF Class.

        1. Set commodity
        2. Set properties
        3. Get DataFrame from Yahoo!Finance for relevant commodity
        4. Create 'Full' DataFrame for GnuCash, \
        including both SQL-relevant and CSV-relevant columns and values.

        Args:
            commodity: GnuCash commodity
            currency: GnuCash book default/base currency
            data_cfg: Yahoo!Finance Data options

        """

        self._commodity = commodity
        self._currency = currency
        self._start_date = data_cfg.start_date
        self._end_date = data_cfg.end_date
        self._period = data_cfg.period

        self._get_yf()
        self._set_full()

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
        if self._commodity.namespace == 'CURRENCY':
            yf_symbol = self._commodity.mnemonic + self._currency + '=X'
        else:
            yf_symbol = self._commodity.mnemonic

        if self._start_date:
            self._yf_df = yfinance.Ticker(yf_symbol).history(
                start = self._start_date, end = self._end_date)
        else:
            if self._period == 'auto':
                start_date = self._commodity.last_price_date + timedelta(1)
                self._yf_df = yfinance.Ticker(yf_symbol).history(
                    start = start_date, end = self._end_date)
            else:
                self._yf_df = yfinance.Ticker(yf_symbol).history(self._period)

    def _set_full(self) -> None:
        """Create Full DataFrame by processing and enriching Yahoo!Finance DataFrame"""
        if (not self.yf_df.empty and self._commodity.mnemonic != self._currency):
            self._full_df = self.yf_df[['Close']].copy()
            self._full_df.index = self.full_df.index.tz_localize(None)
            self._full_df.index.name = 'date'
            self._full_df['Curr'] = self._currency
            self._full_df['Symbol'] = self._commodity.mnemonic
            self._full_df['Full_Name'] = self._commodity.fullname
            self._full_df['Namespace'] = self._commodity.namespace
            if self._commodity.namespace == 'CURRENCY':
                self._full_df['Close'] = self.full_df['Close'].round(decimals = 5)
            else:
                self._full_df['Close'] = self.full_df['Close'].round(decimals = 2)
            self._full_df['guid'] = [uuid.uuid4().hex for _ in range(len(self.full_df.index))]
            self._full_df['commodity_guid'] = self._commodity.guid
            self._full_df['currency_guid'] = self._commodity.currency_guid
            self._full_df['source'] = 'user:price'
            self._full_df['type'] = 'last'
            self._full_df['value_num'] = self.full_df['Close'] * self._commodity.value_denom
            self._full_df['value_denom'] = self._commodity.value_denom
        else:
            self._full_df = pandas.DataFrame()
