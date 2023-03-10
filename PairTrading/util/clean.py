from PairTrading.util.read import getRecentlyClosed
from PairTrading.util.write import dumpRecentlyClosed

from datetime import datetime, date 
import logging 

logger = logging.getLogger(__name__)


def cleanClosedTrades() -> None:    
    closedTrades:dict[str, date] = getRecentlyClosed()
    if not closedTrades:
        logger.info("There are no trades that were closed less than 31 days ago")
        return 
    today:date = date.today()
    
    delNum:int = 0
    for symbol, time in closedTrades.items():
        if (today - time).days > 30:
            del closedTrades[symbol]
            delNum += 1
            
    dumpRecentlyClosed(closedTrades)
    logger.info(f"{delNum} past trading records removed")
    