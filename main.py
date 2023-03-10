from PairTrading.util import cleanClosedTrades, getPairsFromTrainingJson, writeToJson
from PairTrading.trading import TradingManager
from lib.dataEngine import AlpacaDataClient
from authentication.auth import AlpacaAuth, EodAuth
from authentication.authLoader import getAuth
from PairTrading.pairs.createpairs import PairCreator
from PairTrading.util.conversion import serializePairData
from config.configloader import configLoader

from alpaca.trading.models import Order

from train import getTrainAssign
from config.model import CONFIG_TYPE, Config
import logging
from pandas import DataFrame, read_csv
from datetime import datetime, date
import time
from tqdm import tqdm
import sys


config:Config = configLoader(CONFIG_TYPE.PAIR_TRADING)
print(config)

if __name__ == "__main__":   
    logging.basicConfig(stream=sys.stdout, format="%(asctime)s - %(message)s", level=logging.INFO)
    logger = logging.getLogger(__name__)
        
    # see if we need to review trades that were recently closed 
    cleanClosedTrades()
    
    # initialize authentication objects 
    alpacaAuth:AlpacaAuth = getAuth("alpaca_main", config.IS_PAPER)
    eodAuth:EodAuth = getAuth("eod")
    # get recently trained final pairs data 
    pairsDict:dict = getPairsFromTrainingJson()
        
    todayTrained:bool = (date.today() - datetime.strptime(pairsDict["time"], "%Y-%m-%d").date()).days == 0
    if (date.today().day==2 and not todayTrained) or (config.REFRESH_DATA and not todayTrained):
        reason:str = "overdue for training" if (date.today().day==2 and not todayTrained) else "manual decision for new training"
        logger.info(f"new training needs to be conducted -- {reason}")
        getTrainAssign(alpacaAuth, eodAuth, config.OVERWRITE_FUNDAMENTALS) 
        # write that the training has been done
        pairsDict["time"] = datetime.today().strftime("%Y-%m-%d")
        pairsDict["final_pairs"] = serializePairData(pairsDict["final_pairs"])
        writeToJson(pairsDict, "saveddata/pairs/pairs.json")
        
    #initialize pair-creator
    logger.info("initializing pair creator")
    cluster:DataFrame = read_csv("saveddata/cluster.csv", index_col=0)
    pairCreator:PairCreator = PairCreator.create(cluster, AlpacaDataClient.create(alpacaAuth))
    
    # initialize trading manager
    manager = TradingManager.create(alpacaAuth, config=config)
    
    timeTillMarketOpens:int = manager.tradingClient.secondsTillMarketOpens  
    while not manager.tradingClient.clock.is_open:
        if 0 < timeTillMarketOpens <= 3600 * 8:
            logger.info("waiting for market to open")
            time.sleep(timeTillMarketOpens + 60)
        elif timeTillMarketOpens > 3600 * 8:
            logger.info("market is not open today")
            sys.exit()
        timeTillMarketOpens:int = manager.tradingClient.secondsTillMarketOpens            

    logger.info("the market is currently open")
    
    # update viable pairs
    logger.info("getting latest pairs")
    trainedPairs = getPairsFromTrainingJson()
    trainDate:date = datetime.strptime(trainedPairs["time"], "%Y-%m-%d").date()
    newPairs:dict = pairCreator.getFinalPairs(trainDate)
    writeToJson(newPairs, "saveddata/pairs/pairs.json")
           
        
    # start trading
    clock = manager.tradingClient.clock
    canOpen:bool = True 
    while clock.is_open:    
        canOpen = True if (clock.next_close - clock.timestamp).total_seconds() < 300 else canOpen
        if len(manager.openedPositions) < manager.maxPositions * 2 and \
        (clock.next_close - clock.timestamp).total_seconds() < 300 and \
        canOpen:
            newPairs:dict = pairCreator.getFinalPairs(trainDate)
            writeToJson(newPairs, "saveddata/pairs/pairs.json")                     
            clock = manager.tradingClient.clock
            if clock.is_open:
                canOpen = manager.openPositions()
            time.sleep(10)
            clock = manager.tradingClient.clock
        if clock.is_open:
            canOpenNext:bool = manager.closePositions()
            canOpen = True if canOpenNext else canOpen
        time.sleep(1)
        clock = manager.tradingClient.clock

        
