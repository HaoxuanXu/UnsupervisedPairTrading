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
        return [equity.symbol for equity in self.tradingClient.allTradableStocks(exchanges=[AssetExchange.ARCA])]

        
