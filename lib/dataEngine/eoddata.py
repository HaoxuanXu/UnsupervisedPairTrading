from eod import EodHistoricalData
from authentication.enums import ConfigType
from lib.patterns import Singleton, Base 

class EodDataClient(Base, metaclass=Singleton):
    
    def __init__(self, auth):
        self.dataClient:EodHistoricalData = EodHistoricalData(auth.api_key)
        
    @classmethod
    def create(cls, auth):
        if not cls._isAuthValid(auth):
            raise ValueError("wrong authentication object detected (not belonging to EOD)")
        return cls(auth)
    
    @staticmethod
    def _isAuthValid(auth) -> bool:
        if auth.configType == ConfigType.EOD and auth.api_key:
            return True 
        return False
    
    def getFundamentals(self, symbol:str) -> dict:
        return self.dataClient.get_fundamental_equity(symbol)