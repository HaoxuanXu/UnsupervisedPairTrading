from lib.tradingClient import AlpacaTradingClient
from lib.dataEngine import AlpacaDataClient
from PairTrading.util.read import readFromJson, getRecentlyClosed, getTradingRecord, getPairsFromTrainingJson
from PairTrading.util.write import writeToJson, dumpRecentlyClosed, dumpTradingRecord
from lib.patterns import Singleton, Base
from PairTrading.trading.helper import PairInfoRetriever
from authentication.auth import AlpacaAuth
from config.model import Config

from alpaca.trading.models import TradeAccount, Position, Order, Clock
from alpaca.data.models import Quote


import os
import pytz
import logging
import numpy as np 
from datetime import date, datetime
from pandas import Series

logger = logging.getLogger(__name__)


class TradingManager(Base, metaclass=Singleton):
    
    def __init__(
        self, 
        tradingClient:AlpacaTradingClient, 
        dataClient:AlpacaDataClient, 
        entryPercent:float, 
        maxPositions:int,
        minPositions:int):
        self.tradingClient:AlpacaTradingClient = tradingClient
        self.dataClient:AlpacaDataClient = dataClient
        self.pairInfoRetriever:PairInfoRetriever = PairInfoRetriever.create(tradingClient)
        self.entryPercent:float = entryPercent
        self.maxPositions:int = maxPositions
        self.minPositions:int = minPositions
        self.openedPositions:dict[str, Position] = self.tradingClient.openedPositions
        self.orderListCache:dict[str:list] = {}
        self.clock:Clock = self.tradingClient.clock
        
    @classmethod
    def create(cls, alpacaAuth:AlpacaAuth, config:Config):
        tradingClient:AlpacaTradingClient = AlpacaTradingClient.create(alpacaAuth)
        dataClient:AlpacaDataClient = AlpacaDataClient.create(alpacaAuth)
        return cls(
            tradingClient=tradingClient,
            dataClient=dataClient,
            entryPercent=config.ENTRYPERCENT,
            maxPositions=config.MAXIMUM_POSITIONS,
            minPositions=config.MINUMUM_POSITIONS
        )
        
    @property 
    def tradingRecord(self) -> dict[tuple, float]:
        return getTradingRecord()
    
    @tradingRecord.setter
    def tradingRecord(self, rec:dict[tuple, float]) -> None:
        dumpTradingRecord(rec)
         
    def _getShortableQty(self, symbol:str, notionalAmount) -> float:
        
        latestPrice:float = self.dataClient.getLastMinute(symbol)
        rawQty:float = notionalAmount // latestPrice
        offset:float = (rawQty % 100) if (rawQty % 100) >= 50 else 0
        return ((rawQty // 100) * 100) + offset
    
    def _getViableTradesNum(self, entryAmount:float, tradingPairs:dict[tuple, list]) -> int:
        res:int = 0
        
        for pair, _ in tradingPairs.items():
            shortQty:float = self._getShortableQty(pair[0], entryAmount)
            if shortQty:
                res += 1 
        return res 
    
    def _getOptimalTradingNum(self, tradingPairs, availableCash:float, openedPositions:dict[str, Position]) -> (int, float):
        if availableCash <= 0:
            return (0, 0)
               
        openedEquities:list = []
        tradingNum:int = 0
        avgEntryAmount:float = 0
        
        if openedPositions:           
            for stock, position in openedPositions.items():
                openedEquities.append(abs(float(position.avg_entry_price) * float(position.qty)))
            openedEquities:np.array = np.array(openedEquities)
            avgEntryAmount:float = (np.sum(openedEquities) + availableCash) // self.maxPositions
            tradingNum:int = min([
                availableCash//avgEntryAmount, 
                self._getViableTradesNum(avgEntryAmount, tradingPairs), 
                self.maxPositions-len(openedPositions) if self.maxPositions-len(openedPositions) > 0 else 0
                ])
                
        else:
            tradingNum:int = self.maxPositions
            avgEntryAmount = availableCash / tradingNum
            while self._getViableTradesNum(avgEntryAmount, tradingPairs) < self.minPositions <= tradingNum:
                tradingNum -= 1
                avgEntryAmount = availableCash / tradingNum
                
            tradingNum:int = self._getViableTradesNum(avgEntryAmount, tradingPairs)
            if tradingNum < self.minPositions:
                logger.warn(f"Too few available pairs enterable ({tradingNum} pairs), aborting entry...")
                return (0, 0)
        
        if tradingNum > len(tradingPairs):
            tradingNum = len(tradingPairs) 

        return (tradingNum, avgEntryAmount)
                  
    
    def openPositions(self) -> None:
        
        if len(self.openedPositions) >= self.maxPositions:
            logger.info(f"portfolio has reached maximum {self.maxPositions} positions ...")
            return 
        
        tradingPairs:dict[tuple, list] = self.pairInfoRetriever.getTradablePairs(
            pairs=self.pairInfoRetriever.trainedPairs, 
            openedPositions=self.openedPositions
        )
        if not tradingPairs:
            logger.info("No trading pairs detected")
            return
       
        tradingAccount:TradeAccount = self.tradingClient.accountDetail
        totalPosition:float = sum([abs(float(p.cost_basis)) for p in self.openedPositions.values()])
        availableCash:float = (min(float(tradingAccount.equity), float(tradingAccount.cash)) * self.entryPercent - totalPosition) / 2
        logger.info(f"available cash: ${round(availableCash, 2)*2}")
        
        tradeNums, notionalAmount = self._getOptimalTradingNum(tradingPairs, availableCash, self.openedPositions)          
        if tradeNums < 1:
            logger.info("No more trades can be placed currently")
            return 
            
        tradingRecord:dict[tuple, float] = self.tradingRecord
        pairsList:list[tuple] = list(tradingPairs.keys())
        executedTrades:int = 0
        for pair in pairsList:
            if executedTrades >= tradeNums:
                break
            try:
                shortOrder, longOrder = self.tradingClient.openArbitragePositions(
                    stockPair=(pair[0], pair[1]), 
                    shortQty=self._getShortableQty(pair[0], notionalAmount)
                )           
                tradingRecord[pair] = self.pairInfoRetriever.trainedPairs[pair]
                logger.info(f"short {pair[0]} long {pair[1]} pair position opened")
                self.tradingRecord = tradingRecord
                executedTrades += 1
            except Exception:
                continue
            
        if executedTrades > 0:
            self.openedPositions = self.tradingClient.openedPositions
        
            
        
    def _getLatestProfit(self, position:Position, is_short:bool) -> float:        
        quote:Quote = self.dataClient.getLatestQuote(position.symbol)
        if is_short:
            return (float(position.avg_entry_price) - quote.ask_price) / float(position.avg_entry_price)
        else:
            return (quote.bid_price - float(position.avg_entry_price)) / float(position.avg_entry_price)
            
                         
                         
    def _getCloseablePairs(self, openedPositions:dict[str, Position]) -> list[tuple]:
        updateLogTime:bool = (datetime.now(self.clock.timestamp.tzinfo) - self.clock.timestamp).seconds >= 60
        res:list[tuple] = []        
        openedPairs:dict[tuple, float] = self.tradingRecord     
        openedPairsPositions:dict[tuple, list] = self.pairInfoRetriever.getCurrentlyOpenedPairs(
            pairs=openedPairs, 
            openedPositions=openedPositions)    
        tradingRecord:dict[tuple, float] = self.tradingRecord 
        
        if not openedPairsPositions:
            logger.info("No pairs opened")
            return
        
        for pair, positions in openedPairsPositions.items():
            
            currProfit:float = (self._getLatestProfit(positions[0], True) + self._getLatestProfit(positions[1], False)) / 2
            ordersList:list[Order] = self.orderListCache[pair] if pair in self.orderListCache else self.tradingClient.getOrders(pair)
            self.orderListCache[pair] = ordersList 
            daysElapsed:int = (date.today() - ordersList[0].submitted_at.date()).days
            
            if updateLogTime:
                logger.info(
                    f"{pair[0]}--{pair[1]}, profit: {round(currProfit*100, 2)}%, days: {daysElapsed}, exit_profit: {round(tradingRecord[pair]*100, 2)}%"
                    )
            
            if currProfit > tradingRecord[pair] or currProfit < -0.1:
                res.append(pair)
            else:                 
                if (daysElapsed > 30 and (self.clock.next_close - self.clock.timestamp).total_seconds() <= 600) or \
                    (daysElapsed == 30 and currProfit > tradingRecord[pair] * 2 / 3) or \
                    (daysElapsed > 30 and currProfit > tradingRecord[pair] / 3):
                    res.append(pair)
                    
        if updateLogTime:
            print()
            print("========================================================================")
            print()
            self.clock:Clock = self.tradingClient.clock 
        return res 
    
    def closePositions(self) -> bool:        
        closeablePairs:list[tuple] = self._getCloseablePairs(self.openedPositions)
        
        if not closeablePairs:
            return False
        
        tradingRecord:dict[tuple, float] = self.tradingRecord
        recentlyClosed:dict[str, date] = self.pairInfoRetriever.recentlyClosedPositions
        
        tradesExecuted:int = 0
        for pair in closeablePairs:
            order1, order2 = self.tradingClient.closeArbitragePositions(pair)
            tradesExecuted += 1
            del tradingRecord[pair]
            recentlyClosed[order1.symbol] = order1.submitted_at.date()
            recentlyClosed[order2.symbol] = order2.submitted_at.date()       
            self.tradingRecord = tradingRecord
            self.pairInfoRetriever.recentlyClosedPositions = recentlyClosed      

            logger.info(f"closed {pair[0]} <-> {pair[1]} pair position.")
            
        if tradesExecuted > 0:
            self.openedPositions = self.tradingClient.openedPositions
        return True
        
        
    
        
    