from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, StockLatestQuoteRequest, StockQuotesRequest, StockLatestBarRequest
from alpaca.data.models import Quote, Bar
from alpaca.data.timeframe import TimeFrame
from alpaca.data.enums import Adjustment, DataFeed
from lib.dataEngine.common import BarCollection
from lib.patterns.singleton import Singleton
from lib.patterns.retry import retry
from lib.patterns.base import Base

import pandas as pd 
import logging 
from datetime import datetime
from numpy import array
from dateutil.relativedelta import relativedelta

logger = logging.getLogger(__name__)

class AlpacaDataClient(Base, metaclass=Singleton):
    
    def __init__(self, auth):
        self.dataClient:StockHistoricalDataClient = StockHistoricalDataClient(
            api_key=auth.api_key,
            secret_key=auth.secret_key
        )   
    
    @classmethod
    def create(cls, auth):
        if cls._isAuthValid(auth):
            return cls(auth=auth)
        else:
            raise AttributeError("the auth object is invalid")
    
    @staticmethod
    def _isAuthValid(auth) -> bool:
        if auth.api_key and auth.secret_key:
            return True 
        return False 
    
    @retry(max_retries=3, retry_delay=60, logger=logger)
    def getMonthly(self, symbol:str, num_months:int=60) -> pd.DataFrame:
        return self.dataClient.get_stock_bars(
            StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame.Month,
                adjustment=Adjustment.ALL,
                feed=DataFeed.SIP,
                start=datetime.today() - relativedelta(months=num_months),
                end=datetime.today()
            )
        ).df 
        
        
    @retry(max_retries=3, retry_delay=60, logger=logger)
    def getWeekly(self, symbol:str) -> pd.DataFrame:
        return self.dataClient.get_stock_bars(
            StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame.Week,
                adjustment=Adjustment.ALL,
                feed=DataFeed.SIP,
                start=datetime.today() - relativedelta(years=3),
                end=datetime.today()
            )
        ).df 
        
    @retry(max_retries=3, retry_delay=60, logger=logger)
    def getDaily(self, symbol:str, endDate:datetime = datetime.today()) -> pd.DataFrame:
        return self.dataClient.get_stock_bars(
            StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame.Day,
                adjustment=Adjustment.ALL,
                feed=DataFeed.SIP,
                limit=30,
                start=endDate - relativedelta(days=30),
                end=endDate
            )
        ).df 
        
    def getHourly(self, symbol:str, endDate:datetime = datetime.now(), days:int = 30) -> pd.DataFrame:
        return self.dataClient.get_stock_bars(
            StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame.Hour,
                adjustment=Adjustment.ALL,
                feed=DataFeed.SIP,
                start=endDate - relativedelta(days=days),
                end=endDate
            )
        ).df
        
    def getMinutes(self, symbol:str, endDate:datetime = datetime.now(), days:int = 1) -> pd.DataFrame:
        return self.dataClient.get_stock_bars(
            StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame.Minute,
                adjustment=Adjustment.ALL,
                feed=DataFeed.SIP,
                start=endDate - relativedelta(days=days)
            )
        ).df
        
    @retry(max_retries=3, retry_delay=60, incremental_backoff=2, logger=logger)
    def getLastMinute(self, symbol:str) -> float:
        return self.dataClient.get_stock_latest_bar(
            StockLatestBarRequest(
                symbol_or_symbols=symbol,
                feed=DataFeed.SIP
            )
        )[symbol].close
        
    def getMarketCap(self, symbol:str) -> float:
        df:pd.DataFrame = self.getDaily(symbol)
        return (df["vwap"] * df["volume"]).mean()
        
    @retry(max_retries=3, retry_delay=60, incremental_backoff=2, logger=logger)
    def getLongDaily(self, symbol:str, endDate:datetime = datetime.today()) -> pd.DataFrame:
        return self.dataClient.get_stock_bars(
            StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame.Day,
                adjustment=Adjustment.ALL,
                feed=DataFeed.SIP,
                limit=90,
                start=endDate - relativedelta(days=90),
                end=endDate
            )
        ).df
        
    def getAllBars(self, symbol:str) -> BarCollection:
        daily:pd.DataFrame = self.getDaily(symbol)
        weekly:pd.DataFrame = self.getWeekly(symbol)
        monthly:pd.DataFrame = self.getMonthly(symbol)      
        return BarCollection(daily, weekly, monthly)
    
    def getLatestQuote(self, symbol:str) -> Quote:
        return self.dataClient.get_stock_latest_quote(
            StockLatestQuoteRequest(
                symbol_or_symbols=symbol,
                feed=DataFeed.SIP
            )
        )[symbol]
        