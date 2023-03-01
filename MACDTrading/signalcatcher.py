from ta.trend import MACD, SMAIndicator
from ta.volatility import AverageTrueRange
from lib.dataEngine import AlpacaDataClient
from pandas import Series, DataFrame
from datetime import datetime, date 
from lib.patterns.retry import retry


from dateutil.relativedelta import relativedelta
from alpaca.trading.models import Position, Order
import copy 
import logging 

logger = logging.getLogger(__name__)


class SignalCatcher:
    
    def __init__(self, dataClient:AlpacaDataClient):
        self.client:AlpacaDataClient = dataClient 
        
    @classmethod
    def create(cls, dataClient:AlpacaDataClient):
        return cls(
            dataClient=dataClient
        )
        
        
        
    def _getFastSma(self, profitPercent:float, closePrice:Series) -> Series:
        fastSma:Series = None 
        
        if profitPercent < 0.2:
            fastSma = SMAIndicator(
            close=closePrice, 
            window=31
            ).sma_indicator()
        elif  0.4 > profitPercent >= 0.2:
            fastSma = SMAIndicator(
            close=closePrice, 
            window=26
            ).sma_indicator()
        elif profitPercent >= 0.4:
            fastSma = SMAIndicator(
            close=closePrice, 
            window=21
            ).sma_indicator()
        
        
    def getATR(self, symbol:str) -> float:
        priceDF = self.client.getDaily(symbol)
        avr = AverageTrueRange(
            high=priceDF["high"], 
            low=priceDF["low"], 
            close=priceDF["close"]
        )
        return avr.average_true_range().iloc[-1]
        
          
    def canOpen(self, symbol:str) -> bool:
          
        try:
            dailyBars:Series = self.client.getLongDaily(symbol)
        except Exception as ex:
            print(f"{symbol}: {ex}")
            return False 
        
        
        macd:Series = MACD(
            close=dailyBars["close"]
        ).macd().loc[symbol].dropna()
        
        if macd.size < 31:
            return False 
        
        
        return (
                (macd.iloc[-2:] > 0).any() and 
                (macd.iloc[-31:-2] >= 0).sum() == 0  
            )
    
    @retry(max_retries=3, retry_delay=60, logger=logger) 
    def canClose(self, symbol:str, position:Position, order:Order, secondsTillMarketClose:int)-> bool:
        closePrice:Series = self.client.getLongDaily(symbol)["close"]
        latestClose:float = self.client.getLatestQuote(symbol).bid_price  
        profitPercent:float = (latestClose - float(position.avg_entry_price)) / float(position.avg_entry_price)
        
        fastSma:Series = self._getFastSma(profitPercent, closePrice)                 
        daysElapsed = (date.today() - order.submitted_at.date()).days      
        stopLoss:float = fastSma.iloc[-1]    
        
        return (latestClose < stopLoss and secondsTillMarketClose < 600)
