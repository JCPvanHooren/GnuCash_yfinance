import yfinance
from datetime import timedelta
import pandas
import uuid

class DF:
    def __init__(self, commodity, currency, start_date, end_date, period):    
        self._commodity = commodity
        self._currency = currency
        self._start_date = start_date
        self._end_date = end_date
        self._period = period
        
        self._get_yf()
        self._set_full()
    
    @property
    def commodity(self):
        return self._commodity
    
    @property
    def currency(self):
        return self._currency
    
    @property
    def start_date(self):
        return self._start_date
    
    @property
    def end_date(self):
        return self._end_date
    
    @property
    def period(self):
        return self._period
    
    @property
    def yf_df(self):
        return self._yf_df
    
    @property
    def full_df(self):
        return self._full_df
    
    @property
    def stdout_df(self):
        return self.full_df[['Curr', 'Close']]
    
    @property
    def sql_df(self):
        return self.full_df[['guid', 'commodity_guid', 'currency_guid', 'source', 'type', 'value_num', 'value_denom']]
    
    def _get_yf(self):       
        if self.commodity.namespace == 'CURRENCY':
            yf_symbol = self.commodity.mnemonic + self.currency + '=X'
        else:
            yf_symbol = self.commodity.mnemonic
        
        if self.start_date:
            self._yf_df = yfinance.Ticker(yf_symbol).history(start = self.start_date, end = self.end_date)
        else:
            if self.period == 'auto':
                start_date = self.commodity.last_price_date + timedelta(1)
                self._yf_df = yfinance.Ticker(yf_symbol).history(start = start_date, end = self.end_date)
            else:
                self._yf_df = yfinance.Ticker(yf_symbol).history(self.period)
    
    def _set_full(self):
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