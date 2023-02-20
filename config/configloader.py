import yaml
from config.model import Config, CONFIG_TYPE


def configLoader(configType:CONFIG_TYPE) -> Config:
    
    if configType == CONFIG_TYPE.PAIR_TRADING:

        with open(f"config/pairtrading_config.yaml", "r") as inFile:
            configDict:dict = yaml.load(inFile, Loader=yaml.Loader)
            
        return Config(
            ENTRYPERCENT=configDict["entry_percent"],
            REFRESH_DATA=configDict["refresh_data"],
            OVERWRITE_FUNDAMENTALS=configDict["overwrite_fundamentals"],
            MAXIMUM_POSITIONS=configDict["maximum_positions"],
            MINUMUM_POSITIONS=configDict["minimum_positions"],
            IS_PAPER=configDict["is_paper"]
        )
        
    elif configType == CONFIG_TYPE.MACD_TRADING:
        with open(f"config/macd_config.yaml", "r") as inFile:
            configDict:dict = yaml.load(inFile, Loader=yaml.Loader)
            
        return Config(
            ENTRYPERCENT=configDict["entry_percent"],
            IS_PAPER=configDict["is_paper"],
            REFRESH_DATA=False,
            OVERWRITE_FUNDAMENTALS=False       
        )