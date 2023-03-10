from authentication.base import BaseAuth
from authentication.enums import ConfigType

class AlpacaAuth(BaseAuth):
    def __init__(self, api_key, secret_key:str, configType, isPaper:bool=True):
        super().__init__(api_key, secret_key)
        self.configType = configType
        self.isPaper:bool = isPaper
        
    @classmethod
    def create(cls, rawDict, isPaper:bool, configType:str):
        if isPaper:
            return cls(
                api_key=rawDict["paper"]["api_key"],
                secret_key=rawDict["paper"]["secret_key"],
                configType=configType,
                isPaper=True)
        else:
            return cls(
                api_key=rawDict["live"]["api_key"],
                secret_key=rawDict["live"]["secret_key"],
                configType=configType,
                isPaper=False)
        
    def __str__(self):
        return str({
            "type": self.configType,
            "api_key": self.api_key,
            "secret_key": self.secret_key
        })
    
        
class EodAuth(BaseAuth):
    def __init__(self, api_key:str):
        super().__init__(api_key, None)
        self.configType = ConfigType.EOD
        
    @classmethod
    def create(cls, rawDict, isPaper=True):
        return cls(
            api_key=rawDict["api_key"])
        
    def __str__(self):
        return str({
            "type": self.configType,
            "api_key": self.api_key
        })