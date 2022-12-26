from PairTrading.lib.tradingClient import AlpacaTradingClient
from PairTrading.lib.dataEngine import AlpacaDataClient
from PairTrading.util.read import readFromJson, getRecentlyClosed, getTradingRecord, getPairsFromTrainingJson
from PairTrading.util.write import writeToJson, dumpRecentlyClosed, dumpTradingRecord
from PairTrading.util.patterns import Singleton, Base
from PairTrading.trading.helper import PairInfoRetriever
from PairTrading.authentication import AlpacaAuth

from alpaca.trading.models import TradeAccount, Position, Order


import os
import logging
from datetime import date, datetime

logger = logging.getLogger(__name__)


class TradingManager(Base, metaclass=Singleton):
    
    def __init__(self, tradingClient:AlpacaTradingClient, dataClient:AlpacaDataClient, entryPercent:float):
        self.tradingClient:AlpacaTradingClient = tradingClient
        self.dataClient:AlpacaDataClient = dataClient
        self.pairInfoRetriever:PairInfoRetriever = PairInfoRetriever.create(tradingClient)
        self.entryPercent:float = entryPercent
        
    @classmethod
    def create(cls, alpacaAuth:AlpacaAuth, entryPercent:float):
        tradingClient:AlpacaTradingClient = AlpacaTradingClient.create(alpacaAuth)
        dataClient:AlpacaDataClient = AlpacaDataClient.create(alpacaAuth)
        return cls(
            tradingClient=tradingClient,
            dataClient=dataClient,
            entryPercent=entryPercent
        )
        
    @property 
    def tradingRecord(self) -> dict[tuple, float]:
        return getTradingRecord()
    
    @tradingRecord.setter
    def tradingRecord(self, rec:dict[tuple, float]) -> None:
        dumpTradingRecord(rec)
         
    def _getShortableQty(self, symbol:str, notionalAmount) -> float:
        latestBidPrice:float = self.dataClient.getLatestQuote(symbol).bid_price
        rawQty:float = notionalAmount // latestBidPrice
        offset:float = (rawQty % 100) if (rawQty % 100) >= 50 else 0
        return ((rawQty // 100) * 100) + offset
    
    def _getViableTradesNum(self, entryAmount:float) -> int:
        res:int = 0
        
        for pair, _ in self.pairInfoRetriever.trainedPairs.items():
            if self._getShortableQty(pair[0], entryAmount):
                res += 1 
                
        return res 
    
    def _getOptimalTradingNum(self, tradingPairs, availableCash:float, currOpenedPositions:dict[str, Position]) -> (int, float):
        if availableCash <= 0:
            return (0, 0)
        res:int = 0
        if currOpenedPositions:           
            tmp:float = 0
            for stock, position in currOpenedPositions.items():
                tmp += abs(float(position.avg_entry_price) * float(position.qty))
            avgEntryAmount = tmp / len(currOpenedPositions)
            res = min(availableCash//avgEntryAmount, self._getViableTradesNum(avgEntryAmount))
        else:
            tradingNum:int = len(tradingPairs)
            avgEntryAmount = availableCash / tradingNum
            while tradingNum > self._getViableTradesNum(avgEntryAmount):
                tradingNum -= 1
                avgEntryAmount = availableCash / tradingNum
            res = tradingNum
        
        if res > len(tradingPairs):
            res = len(tradingPairs)
            avgEntryAmount = availableCash / res 
        return (res, avgEntryAmount)
                  
    
    def openPositions(self) -> None:
        
        currOpenedPositions:dict[str, Position] = self.tradingClient.openedPositions
        tradingPairs:dict[tuple, list] = self.pairInfoRetriever.getTradablePairs(
            pairs=self.pairInfoRetriever.trainedPairs, 
            openedPositions=currOpenedPositions
        )
        if not tradingPairs:
            logger.debug("No trading pairs detected")
            return
       
        tradingAccount:TradeAccount = self.tradingClient.accountDetail
        totalPosition:float = sum([abs(float(p.cost_basis)) for p in currOpenedPositions.values()])
        availableCash:float = (float(tradingAccount.cash) * self.entryPercent - totalPosition) / 2
        logger.info(f"available cash: ${round(availableCash, 2)*2}")
        
        tradeNums, notionalAmount = self._getOptimalTradingNum(tradingPairs, availableCash, currOpenedPositions)           
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
                shortOrder, longOrder = self.tradingClient.openPositions(
                    stockPair=(pair[0], pair[1]), 
                    shortQty=self._getShortableQty(pair[0], notionalAmount)
                )           
                tradingRecord[pair] = self.pairInfoRetriever.trainedPairs[pair][1]
                logger.info(f"short {pair[0]} long {pair[1]} pair position opened")
                self.tradingRecord = tradingRecord
                executedTrades += 1
            except:
                continue
        
            
        
            
                         
                         
    def _getCloseablePairs(self, currOpenedPositions:dict[str, Position]) -> list[tuple]:
        res:list[tuple] = []        
        openedPairs:dict[tuple, float] = self.tradingRecord     
        openedPairsPositions:dict[tuple, list] = self.pairInfoRetriever.getCurrentlyOpenedPairs(
            pairs=openedPairs, 
            openedPositions=currOpenedPositions)     
        
        if not openedPairsPositions:
            logger.debug("No pairs opened")
            return
        
        for pair, positions in openedPairsPositions.items():
            meanPriceRatio:float = openedPairs[pair]
            currPriceRatio:float = float(positions[0].current_price) / float(positions[1].current_price)
            logger.info(f"{pair[0]}--{pair[1]}: curr_ratio: {currPriceRatio}, mean_ratio: {meanPriceRatio}")
            if currPriceRatio <= meanPriceRatio:
                res.append(pair)
            else:   
                ordersList:list[Order] = self.tradingClient.getPairOrders(pair)
                if (date.today() - ordersList[0].submitted_at.date()).days > 30:
                    res.append(pair)
                      
        return res 
    
    def closePositions(self) -> bool:
        currOpenedPositions:dict[str, Position] = self.tradingClient.openedPositions          
        closeablePairs:list[tuple] = self._getCloseablePairs(currOpenedPositions)
        
        if not closeablePairs:
            logger.debug("no closeable pairs detected currently")
            return False
        
        tradingRecord:dict[tuple, float] = self.tradingRecord
        recentlyClosed:dict[str, date] = self.pairInfoRetriever.recentlyClosedPositions
        
        for pair in closeablePairs:
            order1, order2 = self.tradingClient.closePositions(pair)
            del tradingRecord[pair]
            recentlyClosed[order1.symbol] = order1.submitted_at.date()
            recentlyClosed[order2.symbol] = order2.submitted_at.date()       
            self.tradingRecord = tradingRecord
            logger.info(f"recently closed: {recentlyClosed}")
            self.pairInfoRetriever.recentlyClosedPositions = recentlyClosed      

            logger.info(f"closed {pair[0]} <-> {pair[1]} pair position.")
            
        return True
        
        
    
        
    