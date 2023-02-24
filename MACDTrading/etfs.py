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
        # res["NASDAQ"] = [equity.symbol for equity in self.tradingClient.allTradableStocks(exchanges=[AssetExchange.NASDAQ])
        #                     if self.dataClient.getMarketCap(equity.symbol) > 1_000_000]
        res["ETF"] = [equity.symbol for equity in self.tradingClient.allTradableStocks(exchanges=[AssetExchange.ARCA])]
        
        res["NASDAQ"] = []
        res["NYSE_AMEX"] = []
        # res["NYSE_AMEX"] = [equity.symbol for equity in self.tradingClient.allTradableStocks(exchanges=[AssetExchange.NYSE, AssetExchange.AMEX])
        #                     if self.dataClient.getMarketCap(equity.symbol) > 1_000_000]
                
        return res 
        
