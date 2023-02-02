import yaml 
from dataclasses import dataclass, asdict
from enum import Enum

class CONFIG_TYPE(Enum):
    PAIR_TRADING = "pair_trading"
    MACD_TRADING = "macd_trading"

@dataclass 
class Config:
    ENTRYPERCENT: float 
    REFRESH_DATA: bool 
    OVERWRITE_FUNDAMENTALS: bool 
    IS_PAPER: bool 
    
    def __repr__(self):
        return str(asdict(self))
    
