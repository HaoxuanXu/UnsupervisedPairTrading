from PairTrading.util import cleanClosedTrades, getPairsFromTrainingJson
from PairTrading.trading import TradingManager
from PairTrading.authentication.auth import AlpacaAuth, EodAuth
from PairTrading.authentication.authLoader import getAuth

from alpaca.trading.models import Order

from train import getTrainAssign
from datetime import datetime, date
from tqdm import tqdm
import time

ENTRY_PERCENT = 0.3
REFRESH_DATA = False

if __name__ == "__main__":
        
    # see if we need to review trades that were recently closed 
    cleanClosedTrades()
    
    # initialize authentication objects 
    alpacaAuth:AlpacaAuth = getAuth("alpaca")
    eodAuth:EodAuth = getAuth("eod")
    # get recently trained final pairs data 
    pairsDict:dict = getPairsFromTrainingJson()
    
    todayTrained:bool = (date.today() - datetime.strptime(pairsDict["time"], "%Y-%m-%d").date()).days == 0
    if (date.today().day==2 and not todayTrained) or REFRESH_DATA:
        reason:str = "overdue for training" if (date.today().day==2 and not todayTrained) else "manual decision for new training"
        print(f"new training needs to be conducted -- {reason}")
        getTrainAssign(alpacaAuth, eodAuth, True) 
        
    # initialize trading manager
    manager = TradingManager.create(alpacaAuth, ENTRY_PERCENT)
    
    timeTillMarketOpens:int = manager.tradingClient.secondsTillMarketOpens
    
    if timeTillMarketOpens:
        time.sleep(timeTillMarketOpens + 60)
    else:
        print("the market is currently open")
        
    # start trading
    while manager.tradingClient.clock.is_open:
        manager.openPositions()
        manager.closePositions()
        time.sleep(60*10) # sleep for 10 minutes