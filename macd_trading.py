from config.model import Config, CONFIG_TYPE
from config.configloader import configLoader
from authentication.authLoader import getAuth
from authentication.auth import AlpacaAuth
from lib.dataEngine import AlpacaDataClient
from lib.tradingClient import AlpacaTradingClient
from alpaca.trading.models import Position

from MACDTrading import MACDManager, ETFs
import logging
from datetime import datetime
from dateutil.relativedelta import relativedelta
import time
import sys
from tqdm import tqdm
import argparse 

logging.basicConfig(stream=sys.stdout, format="%(asctime)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

parser = argparse.ArgumentParser()
parser.add_argument("--live_or_paper", help="choose whether to trade on live or paper account")
args = parser.parse_args()

config:Config = configLoader(configType=CONFIG_TYPE.MACD_TRADING)
config.IS_PAPER = (args.live_or_paper.strip().lower() != "live") 
logger.info(config)

alpacaAuth:AlpacaAuth = getAuth("alpaca_side", config.IS_PAPER)
dataClient:AlpacaDataClient = AlpacaDataClient.create(alpacaAuth)
tradingClient:AlpacaTradingClient = AlpacaTradingClient.create(alpacaAuth)

manager:MACDManager = MACDManager.create(
    dataClient=dataClient, 
    tradingClient=tradingClient, 
    entryPercent=config.ENTRYPERCENT)


if __name__ == "__main__":
    openedPositions:dict[str, Position] = tradingClient.openedPositions
    timeTillMarketOpens:int = manager.tradingClient.secondsTillMarketOpens  
    while not manager.tradingClient.clock.is_open:
        if 0 < timeTillMarketOpens <= 3600 * 8:
            logger.info("waiting for market to open")
            time.sleep(timeTillMarketOpens + 60 * 10)
        elif timeTillMarketOpens > 3600 * 8:
            logger.info("market is not open today")
            sys.exit()
        else:
            logger.info(f"anomaly... {round(timeTillMarketOpens/60, 2)} minutes before market opens")
            time.sleep(300*60 + timeTillMarketOpens)
        timeTillMarketOpens:int = manager.tradingClient.secondsTillMarketOpens   
        
    
    
    logger.info("start trading ... ")
    enteredToday:list = []
    clock = manager.tradingClient.clock
    while clock.is_open:
        if (clock.next_close - clock.timestamp).total_seconds() < 3 * 60:
            entered:list = manager.openPositions()
            enteredToday += entered
        manager.closePositions(openedToday=enteredToday)
        time.sleep(5)
        clock = manager.tradingClient.clock

