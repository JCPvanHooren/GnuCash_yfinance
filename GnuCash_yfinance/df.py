"""Manage Pandas DataFrames

.. _Google Python Style Guide:
   http://google.github.io/styleguide/pyguide.html

"""

from datetime import timedelta
import uuid

import pandas
import yfinance

import config

class CommodityDataFrame:
    """Class to store Pandas Dataframes for a Commodity."""
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

        self._yf_df = self._get_yf()
        self._full_df = self._set_full()

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

    def _get_yf(self) -> pandas.DataFrame:
        """Get DataFrame from Yahoo!Finance for relevant commodity

        Returns:
            Pandas DataFrame with prices from Yahoo!Finance for the relevant commodity.

        """

        yf_df = pandas.DataFrame()
        
        if self._commodity.namespace == 'CURRENCY':
            yf_symbol = self._commodity.mnemonic + self._currency + '=X'
        else:
            yf_symbol = self._commodity.mnemonic

        if self._start_date:
            yf_df = yfinance.Ticker(yf_symbol).history(
                start = self._start_date, end = self._end_date
            )
        elif self._period == 'auto':
            start_date = self._commodity.last_price_date + timedelta(1)
            try:
                yf_df = yfinance.Ticker(yf_symbol).history(
                    start = start_date, end = self._end_date
                )
            except IndexError:
                print("No price data found.")
        else:
            yf_df = yfinance.Ticker(yf_symbol).history(self._period)
        
        return yf_df

    def _set_full(self) -> pandas.DataFrame:
        """Create Full DataFrame by processing and enriching Yahoo!Finance DataFrame
        
        Returns:
            Pandas DataFrame with all data for relevant commodity.
        
        """

        full_df = pandas.DataFrame()
        
        if (
            not self.yf_df.empty
            and self._commodity.mnemonic != self._currency
        ):
            full_df = pandas.DataFrame()
            full_df = self.yf_df[['Close']].copy()
            full_df.index = full_df.index.tz_localize(None)
            full_df.index.name = 'date'
            full_df['Curr'] = self._currency
            full_df['Symbol'] = self._commodity.mnemonic
            full_df['Full_Name'] = self._commodity.fullname
            full_df['Namespace'] = self._commodity.namespace
            if self._commodity.namespace == 'CURRENCY':
                full_df['Close'] = full_df['Close'].round(decimals = 5)
            else:
                full_df['Close'] = full_df['Close'].round(decimals = 2)
            full_df['guid'] = [uuid.uuid4().hex for _ in range(len(full_df.index))]
            full_df['commodity_guid'] = self._commodity.guid
            full_df['currency_guid'] = self._commodity.currency_guid
            full_df['source'] = 'user:price'
            full_df['type'] = 'last'
            full_df['value_num'] = full_df['Close'] * self._commodity.value_denom
            full_df['value_denom'] = self._commodity.value_denom
        
        return full_df
