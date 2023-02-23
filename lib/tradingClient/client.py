from authentication.auth import AlpacaAuth
from authentication.enums import ConfigType
from PairTrading.util.read import getRecentlyClosed
from lib.patterns import Singleton, Base 

from alpaca.trading.client import TradingClient
from alpaca.trading.enums import AssetClass, AssetExchange, AssetStatus, OrderSide, TimeInForce, OrderStatus
from alpaca.trading.requests import GetAssetsRequest, MarketOrderRequest, GetOrdersRequest
from alpaca.trading.models import Order, Position, TradeAccount, Asset, Clock

from datetime import date, datetime, timezone
from lib.patterns.retry import retry
import time
import logging 

logger = logging.getLogger(__name__)

class AlpacaTradingClient(Base, metaclass=Singleton):
    
    def __init__(self, auth:AlpacaAuth):
        self.client:TradingClient = TradingClient(
            api_key=auth.api_key,
            secret_key=auth.secret_key,
            paper=auth.isPaper
        ) 
        self._allStocks:list[Asset] = self.client.get_all_assets(
            GetAssetsRequest(
                status=AssetStatus.ACTIVE,
                asset_class=AssetClass.US_EQUITY
            )
        )
    
    @classmethod
    def create(cls, alpacaAuth:AlpacaAuth):
        if alpacaAuth.configType not in (ConfigType.ALPACA_MAIN, ConfigType.ALPACA_SIDE):
            raise AttributeError("the auth object is not for Alpaca client")
        return cls(auth=alpacaAuth)
    

    def allTradableStocks(
        self, 
        exchanges:list = [AssetExchange.AMEX, AssetExchange.ARCA, AssetExchange.NYSE, AssetExchange.NASDAQ]) -> list[str]:
        return [asset for asset in self._allStocks if asset.tradable and 
                asset.exchange in exchanges]
    
    @property
    def clock(self) -> Clock:
        return self.client.get_clock()
    
    @property
    def secondsTillMarketCloses(self) -> int:
        clock:Clock = self.clock
        return (clock.next_close - clock.timestamp).total_seconds()
    
    @property
    def secondsTillMarketOpens(self) -> int:
        clock:Clock = self.clock
        
        if clock.is_open:
            return 0
        
        return int((clock.next_open.replace(tzinfo=None) - clock.timestamp.replace(tzinfo=None)).total_seconds())

    
    
    def getViableStocks(self) -> list[str]:
             
        recentlyClosed:dict[str, date] = getRecentlyClosed() if getRecentlyClosed() else {}
        validAssets:list[str] = [asset.symbol for asset in self.allTradableStocks() if (asset.fractionable==True and \
                                            asset.shortable==True and \
                                            asset.easy_to_borrow==True and \
                                            asset.exchange in (AssetExchange.NYSE, AssetExchange.AMEX, AssetExchange.NASDAQ) and \
                                            "." not in asset.symbol and \
                                            asset.symbol not in recentlyClosed)] 
        
        return validAssets
    
    @property
    def accountDetail(self) -> TradeAccount:
        return self.client.get_account()
    
    @property
    def openedPositions(self) -> dict[str, Position]:        
        openPositions:list[Position] = self.client.get_all_positions()
        res:dict[str, Position] = {position.symbol:position for position in openPositions}
        return res
    
    @retry(max_retries=3, retry_delay=60, incremental_backoff=3, logger=logger)
    def getOrders(self, symbols:tuple) -> list[Order]:
        
        orders = self.client.get_orders(
            GetOrdersRequest(
                status="closed",
                symbols=list(symbols)
            )
        )
        
        return [order for order in orders if order.status == "filled"]

        
    @retry(max_retries=3, retry_delay=1, incremental_backoff=3, logger=logger)   
    def _submitTrade(self, stockSymbol:str, is_notional:bool, qty:float, side:OrderSide) -> Order:  
        if is_notional:
            return self.client.submit_order(order_data=MarketOrderRequest(
                    symbol=stockSymbol,
                    notional=qty,
                    side=side.BUY,
                    time_in_force=TimeInForce.DAY
                ))
        else:            
            return self.client.submit_order(order_data=MarketOrderRequest(
                        symbol=stockSymbol,
                        qty=qty,
                        side=side,
                        time_in_force=TimeInForce.DAY            
                    ))
            
    @retry(max_retries=3, retry_delay=1, incremental_backoff=3, logger=logger)
    def _closePosition(self, symbol:str) -> Order:
        return self.client.close_position(symbol)
        
        
    def openMACDPosition(self, symbol:str, entryAmount:float) -> Order:     
        if entryAmount < 0:
            raise ValueError(f"entry amount: ${round(entryAmount, 2)}  entry amount must be positive")
        
        return self._submitTrade(
            stockSymbol=symbol, 
            is_notional=False, 
            qty=entryAmount, 
            side=OrderSide.BUY
            )
        
              
            
    def closeMACDPosition(self, symbol:str) -> Order:
        return self._closePosition(symbol)
    
   
    
    def openArbitragePositions(self, stockPair:tuple, shortQty:float) -> tuple[Order, Order]:
        
        if shortQty < 1:
            raise ValueError(f"{stockPair[0]} - {stockPair[1]}: insufficient shares number forecasted")
        
        # short the first stock
        shortOrder:Order = self._submitTrade(
            stockSymbol=stockPair[0], 
            is_notational=False,
            qty=shortQty, 
            side=OrderSide.SELL)
        
        time.sleep(1)
        filledShortOrder:Order = self.client.get_order_by_id(shortOrder.id)
        longNotional:float = float(filledShortOrder.filled_qty) * float(filledShortOrder.filled_avg_price)
        
        # long the second stock
        longOrder:Order = self._submitTrade(
            stockSymbol=stockPair[1], 
            is_notational=True, 
            qty=longNotional, 
            side=OrderSide.BUY)

        time.sleep(1)
        filledLongOrder:Order = self.client.get_order_by_id(longOrder.id)
        return (filledShortOrder, filledLongOrder)
    
    def closeArbitragePositions(self, stockPair:tuple) -> tuple[Order, Order]:
        
        # closed short position
        closedShortOrder:Order = self._closePosition(stockPair[0])
        
        # closed long position
        closedLongOrder:Order = self._closePosition(stockPair[1])
        
        return (closedShortOrder, closedLongOrder)
