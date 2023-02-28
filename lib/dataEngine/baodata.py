import baostock as bs 
from lib.patterns.base import Base
from lib.patterns.singleton import Singleton

class BaoDataClient(base, metaclass=Singleton):
    def __init__(self):
        self.client:bs = bs 
        self.client.login()
        
    @classmethod
    def create(cls):
        return cls()
    
    
    