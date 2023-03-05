import gmtrade.api as client 
from gmtrade.api.storage import Account
from gmtrade.api.trade import Position
from gmtrade.enum import (
    OrderType_Market, 
    OrderSide_Buy,
    OrderSide_Sell,
    PositionSide_Long, 
    PositionSide_Short,
    PositionEffect_CloseToday,
    PositionEffect_Open
)
from lib.patterns.base import Base
from lib.patterns.retry import retry
from lib.patterns.singleton import Singleton
import logging 

logger = logging.getLogger(__name__)


class GMTradingClient(Base, metaclass=Singleton):
    
    def __init__(self, token:str, account_id:str, endpoint:str):
        self.client = client 
        self.client.set_token(token=token)
        self.client.set_endpoint(endpoint)
        self.account:Account = self.client.account(account_id=account_id)
        self.client.login(self.account)
    
    @classmethod
    def create(cls):
        return cls()
    
    
    @retry(max_retries=3, retry_delay=10, incremental_backoff=3, logger=logger)
    def getPositions(self) -> list:
        return self.client.get_positions(self.account)
    
    @retry(max_retries=3, retry_delay=10, incremental_backoff=3, logger=logger)
    def openLong(self, stockSymbol:str, entryPercent:float, is_buy:bool):
        stockSymbol = stockSymbol.split(".")[0].upper() + "SE" + "." + stockSymbol.split(".")[1]
        if is_buy:
            self.client.order_percent(
                symbol=stockSymbol, 
                percent=entryPercent, 
                side=OrderSide_Buy, 
                order_type=OrderType_Market, 
                position_effect=PositionEffect_Open)