from PairTrading.util.read import getRecentlyClosed
from PairTrading.util.write import dumpRecentlyClosed

from datetime import datetime, date 
import logging 
import copy

logger = logging.getLogger(__name__)


def cleanClosedTrades() -> None:    
    closedTrades:dict[str, date] = getRecentlyClosed()
    if not closedTrades:
        logger.info("There are no trades that were closed less than 31 days ago")
        return 
    today:date = date.today()
    
    delNum:int = 0
    res = copy.deepcopy(closedTrades)
    for symbol, time in closedTrades.items():
        if (today - time).days > 30:
            del res[symbol]
            delNum += 1
            
    dumpRecentlyClosed(res)
    logger.info(f"{delNum} past trading records removed")
    