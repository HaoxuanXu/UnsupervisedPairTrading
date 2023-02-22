from ta.trend import MACD, SMAIndicator
from ta.volatility import AverageTrueRange
from lib.dataEngine import AlpacaDataClient
from pandas import Series, DataFrame
from datetime import datetime, date 

from dateutil.relativedelta import relativedelta
from alpaca.trading.models import Position, Order
import copy 


class SignalCatcher:
    
    def __init__(self, dataClient:AlpacaDataClient):
        self.client:AlpacaDataClient = dataClient 
        
    @classmethod
    def create(cls, dataClient:AlpacaDataClient):
        return cls(
            dataClient=dataClient
        )
        
    def isIndexUp(self) -> dict[str, bool]:
        nasdaqLatest:float = self.client.getLastMinute("QQQ")
        sp500Latest:float = self.client.getLastMinute("SPY")
        diaLatest:float = self.client.getLastMinute("DIA")
        
        nasdaq21Sma:float = SMAIndicator(
            close=self.client.getDaily("QQQ"), 
            window=21).iloc[-1]
        
        sp50021Sma:float = SMAIndicator(
            close=self.client.getDaily("SPY"), 
            window=21).iloc[-1]
        
        dia21Sma:float = SMAIndicator(
            close=self.client.getDaily("SPY"), 
            window=21).iloc[-1]
        
        res = {}
        res["NASDAQ"] = nasdaqLatest > nasdaq21Sma
        res["SP500"] = sp500Latest > sp50021Sma
        res["DIA"] = diaLatest > dia21Sma
        
        return res 
        
        
        
    def _getFastSma(self, profitPercent:float, closePrice:Series) -> Series:
        fastSma:Series = None 
        
        if profitPercent < 0.2:
            fastSma = SMAIndicator(
            close=closePrice, 
            window=31
            ).sma_indicator()
        elif 0.3 > profitPercent >= 0.2:
            fastSma = SMAIndicator(
            close=closePrice, 
            window=26
            ).sma_indicator()
        elif  0.4 > profitPercent >= 0.3:
            fastSma = SMAIndicator(
            close=closePrice, 
            window=21
            ).sma_indicator()
        elif 0.5 > profitPercent >= 0.4:
            fastSma = SMAIndicator(
            close=closePrice, 
            window=16
            ).sma_indicator()
        elif profit >= 0.5:
            fastSma = SMAIndicator(
            close=closePrice, 
            window=11
            ).sma_indicator()
            
        return fastSma
        
        
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
            minuteBars = self.client.getMinutes(symbol).loc[symbol].loc[date.today().strftime("%Y-%m-%d")]
        except Exception as ex:
            print(f"{symbol}: {ex}")
            return False 
        
        todayOpen:float = minuteBars.iloc[0]["open"]
        latestClose:float = minuteBars.iloc[-1]["close"]
        
        macdCurr:Series = MACD(
            close=dailyBars["close"]
        ).macd().loc[symbol]
        
        macdPrev:Series = copy.deepcopy(macdCurr)
        while macdPrev.index[-1].date() >= date.today():
            macdPrev = macdPrev.iloc[:-1]
        
        
        return (
                macdCurr.loc[date.today().strftime("%Y-%m-%d")][0] > 0 and 
                (macdPrev.iloc[-31:] >= 0).sum() == 0 and 
                latestClose > todayOpen 
            )
        
    def canClose(self, symbol:str, position:Position, order:Order, secondsTillMarketClose:int)-> bool:
        closePrice:Series = self.client.getLongDaily(symbol)["close"]
        latestClose:float = self.client.getLatestQuote(symbol).bid_price  
        profitPercent:float = (latestClose - float(position.avg_entry_price)) / float(position.avg_entry_price)
        
        fastSma:Series = self._getFastSma(profitPercent, closePrice)                 
        daysElapsed = (date.today() - order.submitted_at.date()).days      
        stopLoss:float = fastSma.iloc[-1]    
        
        return (latestClose < stopLoss and secondsTillMarketClose < 600) or (daysElapsed <= 3 and profitPercent >= 0.15) or \
            (daysElapsed <= 10 and profitPercent >= 0.3) or (daysElapsed <= 20 and profitPercent >= 0.4)