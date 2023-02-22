from MACDTrading.signalcatcher import SignalCatcher
from MACDTrading.etfs import ETFs
from lib.dataEngine import AlpacaDataClient
from lib.tradingClient import AlpacaTradingClient
from lib.patterns import Base, Singleton
from alpaca.trading.models import Position, Order, TradeAccount
import logging
from pandas import Series
import time 
from datetime import date 

logger = logging.getLogger(__name__)


class MACDManager(Base, metaclass=Singleton):
    
    def __init__(self, dataClient:AlpacaDataClient, tradingClient:AlpacaTradingClient, entryPercent:float):
        self.tradingClient:AlpacaTradingClient = tradingClient
        self.dataClient:AlpacaDataClient = dataClient
        self.entryPercent:float = entryPercent
        self.signalcatcher:SignalCatcher = SignalCatcher.create(self.dataClient)
        self.etfs:ETFs = ETFs.create(
            tradingClient=self.tradingClient, 
            dataClient=self.dataClient)
        
        self.candidates:dict[str, list] = self.etfs.getAllCandidates()
        
    @classmethod
    def create(cls, dataClient:AlpacaDataClient, tradingClient:AlpacaTradingClient, entryPercent:float):
        return cls(
            dataClient=dataClient,
            tradingClient=tradingClient,
            entryPercent=entryPercent
        )

    
    def _getEnterableEquities(self, openedPositions:dict[str, Position]={}) -> list:
        
        logger.info("start retrieving enterable equities ... ")
        start = time.perf_counter()
        isIndexUp:dict[str, bool] = self.signalcatcher.isIndexUp()
        candidates:list = self.candidates["ETF"]
        
        if isIndexUp["NASDAQ"]:
            candidates += self.candidates["NASDAQ"]
        if isIndexUp["SP500"] and isIndexUp["DIA"]:
            candidates += self.candidates["NYSE_AMEX"]
                
        equities = list(Series({stock:self.signalcatcher.getATR(stock) for stock in candidates if stock not in openedPositions.keys() and 
                    self.signalcatcher.canOpen(stock)}).sort_index(ascending=False).index)
        logger.info(f"retrieval complete. time taken: {round((time.perf_counter() - start)/60, 2)} minutes")
            
        return equities
    
    
    def openPositions(self) -> list:
        openedPositions:dict[str, Position] = self.tradingClient.openedPositions
        openedPositionSums:float = sum([abs(float(p.cost_basis)) for p in openedPositions.values()])
        
        tradingAccount:TradeAccount = self.tradingClient.accountDetail
        stockCandidates:list = self._getEnterableEquities(openedPositions)       
        logger.info(f"enterable stocks: {stockCandidates}")
        availableCash:float = float(tradingAccount.equity) * self.entryPercent - openedPositionSums
        logger.info(f"available cash: ${round(availableCash, 2)}")
        
        res:list = []
        
        if self.tradingClient.clock.is_open:
            entryNum:int = min(
                (20 - len(openedPositions)) if (20 - len(openedPositions)) > 0 else 0, 
                len(stockCandidates)
            )
            for i in range(entryNum):
                order = self.tradingClient.openMACDPosition(stockCandidates[i], availableCash/(20-len(openedPositions)))
                logger.info(f"{stockCandidates[i]} bought    ----   entered amount: ${round(float(order.notional), 2)}")
                res.append(stockCandidates[i])
                
        return res
            
            
    
    def _getCloseableStocks(self, openedPositions:dict[str, Position], openedToday:list) -> list:    
        orderList:list = self.tradingClient.getOrders(tuple(openedPositions.keys()))   
        orderDict:dict[str, Order] = {order.symbol:order for order in orderList}
        
        secondsTillClose:int = self.tradingClient.secondsTillMarketCloses
        return [stock for stock in openedPositions.keys() if stock not in openedToday 
                and self.signalcatcher.canClose(stock, openedPositions[stock], orderDict[stock], secondsTillClose) ]
    
    
    def closePositions(self, openedToday:list=[]) -> None:
        openedPositions:dict[str, Position] = self.tradingClient.openedPositions
        closeableStocks:list = self._getCloseableStocks(openedPositions, openedToday=openedToday)
        
        if self.tradingClient.clock.is_open:
            for symbol in closeableStocks:
                self.tradingClient.closeMACDPosition(symbol)
                logger.info(f"{symbol} position closed")