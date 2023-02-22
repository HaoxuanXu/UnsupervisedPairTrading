from lib.dataEngine import AlpacaDataClient
from lib.tradingClient import AlpacaTradingClient
from lib.patterns import Base, Singleton

from alpaca.trading.models import Asset
from alpaca.trading.enums import AssetExchange
from alpaca.trading.requests import GetAssetsRequest


class ETFs(Base, metaclass=Singleton):

    
    def __init__(self, tradingClient: AlpacaTradingClient, dataClient: AlpacaDataClient):
        self.tradingClient: AlpacaTradingClient = tradingClient
        self.dataClient: AlpacaDataClient = dataClient
        
    @classmethod
    def create(cls, tradingClient: AlpacaTradingClient, dataClient: AlpacaDataClient):
        return cls(
            tradingClient=tradingClient,
            dataClient=dataClient
        )
        
    
    
        
    def getAllCandidates(self) -> dict[str, list]:
        
        res:dict[str, list] = {}
        res["NASDAQ"] = [equity for equity in self.tradingClient.allTradableStocks(exchanges=[AssetExchange.NASDAQ])
                            if self.dataClient.getMarketCap(equity) > 1_000_000]
        res["ETF"] = [equity for equity in self.tradingClient.allTradableStocks(exchanges=[AssetExchange.ARCA]) 
                      if self.dataClient.getMarketCap(equity) > 1_000_000]
        res["NYSE_AMEX"] = [equity for equity in self.tradingClient.allTradableStocks(exchanges=[AssetExchange.NYSE, AssetExchange.AMEX])
                            if self.dataClient.getMarketCap(equity) > 1_000_000]
                
        return res 
        
